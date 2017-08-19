import tensorflow as tf
import numpy as np
from utils import *


class GAE():
	def __init__(self, sess, input_size, gamma, lamda, vf_constraint):
		self.sess = sess
		self.input_size = input_size
		self.gamma = gamma
		self.lamda = lamda
		self.vf_constraint = vf_constraint
		self.build_model()

	# Input will be state : [batch size, observation size]
	# And outputs state value function
	def build_model(self):
		print('Initializinig Value function network')
		with tf.variable_scope('VF'):
			self.x = tf.placeholder(tf.float32, [None, self.input_size], name='State')
			# Target 'y' to calculate loss
			self.target = tf.placeholder(tf.float32, [None], name='Target')
			# Model is MLP composed of 3 hidden layer with 100, 50, 25 tanh units
			h1 = LINEAR(self.x, 100, name='h1')
			h1_nl = tf.tanh(h1)
			h2 = LINEAR(h1_nl, 50, name='h2')
			h2_nl = tf.tanh(h2)
			h3 = LINEAR(h2_nl, 25, name='h3')
			h3_nl = tf.tanh(h3)
			self.value = LINEAR(h3_nl, 1, name='h3')

		tr_vrbs = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope='VF')
		for i in len(tr_vrbs):
			print(i.op.name)

		self.loss = tf.reduce_mean(tf.pow(self.target - self.value, 2))
		# Get gradient of objective
		self.grad_objective = FLAT_GRAD(self.value, tr_vrbs)
		# Things to be matrix-vector product calculated
		self.y = tf.placeholder(tf.float32, [None])
		# Note that H is the Hessian of the objective, different with paper where use H as Gauss-Newton approximation to Hessian
		self.HVP = HESSIAN_VECTOR_PRODUCT(self.loss, tr_vrbs, self.y)
		# To adjust weights and bias
		self.get_value = GetValue(self.sess, tr_vrbs)
		self.set_value = SetValue(self.sess, tr_vrbs)

		self.sess.run(tf.global_variables_initializer())

	def get_advantage(self, paths):
		# 'paths' is composed of dictionary of each episode		
		# Get discounted sum of return
		for path in paths:
			# Discounted sum of return from state 's' until done : [batch size, ]
			path["return_sum"] = DISCOUNT_SUM(path["Reward"], self.gamma) 
 
		# Get observation, make it [batch size, observation size]
		self.observation = np.squeeze(np.concatenate([path["Observation"] for path in paths]))
		self.return_sum = np.concatenate([path["return_sum"] for path in paths])
		self.rewards = np.concatenate([path["Reward"] for path in paths])
		self.done = np.concatenate([path["Dond"] for path in paths])
		# Get batch size
		batch_s = tf.shape(self.x)[0]
		# Compute delta_t_V for all timesteps using current parameter
		feed_dict = {self.x:self.observation, self.target:self.return_sum}
		# [batch size,]
		self.value_s = self.sess.run(self.value, feed_dict=feed_dict)
		# If current state is before game done, set value as 0 
		self.value_next_s = np.zeros((batch_s,))
		self.value_next_s[:batch_s-1] = self.value_s[1:]
		self.value_next_s *= (1 - self.done)
		
		# delta_t_V : reward_t + gamma*Value(state_t+1) - Value(state_t) 
		# [batch size, ] (for all timestep in data)
		self.delta_v = self.rewards + self.gamma*self.value_next_s - self.value_s
		
		# Compute advantage estimator for all timesteps
		GAE = DISCOUNT_SUM(self.delta_v, self.gamma*self.lamda)	
		return GAE

	'''
		From page 7 in GAE paper
		Optimize objective functino as in TRPO using conjugate algorithm
		Solving equation (30)
	'''
	def train(self):
		print('Training Value function network')
		feed_dict = {self.x:self.observation, self.target:self.return_sum}
		gradient_objective = self.sess.run(self.grad_objective, feed_dict=feed_dict)
		
		# Function which takes 'y' input returns Hy
		def get_hessian_vector_product(y):
			feed_dict[self.y] = y
			return self.sess.run(self.HVP, feed_dict=feed_dict)

		# '-' term added because objective function aims to minimize : s = -H(-1)*y
		step_direction = CONJUGATE_GRADIENT(get_hesian_vector_product, -y)
		# Analogous to TRPO train part
		constraint_approx = 0.5*step_direction.dot(get_hessian_vector_product(step_direction))
		maximal_step_length = np.sqrt(self.vf_constraint / constraint_approx)
		full_step = maximal_step_length*step_direction	

		def loss(parameter):
			self.set_value(parameter)
			return self.sess.run(self.loss, feed_dict=feed_dict)

		parameter_prev = self.get_value()
		new_parameter = LINE_SEARCH(loss, parameter_prev, full_step)
		self.set_value(new_theta)







	






