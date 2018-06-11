#! /usr/bin/env python3

# Copyright 2018 Intel Corporation.
# The source code, information and material ("Material") contained herein is  
# owned by Intel Corporation or its suppliers or licensors, and title to such  
# Material remains with Intel Corporation or its suppliers or licensors.  
# The Material contains proprietary information of Intel or its suppliers and  
# licensors. The Material is protected by worldwide copyright laws and treaty  
# provisions.  
# No part of the Material may be used, copied, reproduced, modified, published,  
# uploaded, posted, transmitted, distributed or disclosed in any way without  
# Intel's prior express written permission. No license under any patent,  
# copyright or other intellectual property rights in the Material is granted to  
# or conferred upon you, either expressly, by implication, inducement, estoppel  
# or otherwise.  
# Any license under such intellectual property rights must be express and  
# approved by Intel in writing.

from mvnc import mvncapi as mvnc
import sys
import numpy
import cv2
import time
import csv
import os
import sys

dim=(224,224)
EXAMPLES_BASE_DIR='../../'

# ***************************************************************
# get labels
# ***************************************************************
labels_file=EXAMPLES_BASE_DIR+'data/ilsvrc12/synset_words.txt'
labels=numpy.loadtxt(labels_file,str,delimiter='\t')

# ***************************************************************
# configure the NCS
# ***************************************************************
mvnc.global_set_option(mvnc.GlobalOption.RW_LOG_LEVEL, 2)

# ***************************************************************
# Get a list of ALL the sticks that are plugged in
# ***************************************************************
devices = mvnc.enumerate_devices()
if len(devices) == 0:
	print('No devices found')
	quit()

# ***************************************************************
# Pick the first stick to run the network
# ***************************************************************
device = mvnc.Device(devices[0])

# ***************************************************************
# Open the NCS
# ***************************************************************
device.open()

network_blob='graph'

#Load blob
with open(network_blob, mode='rb') as f:
	blob = f.read()

graph = mvnc.Graph('graph')
fifoIn, fifoOut = graph.allocate_with_fifos(device, blob)

# ***************************************************************
# Load the image
# ***************************************************************
ilsvrc_mean = numpy.load(EXAMPLES_BASE_DIR+'data/ilsvrc12/ilsvrc_2012_mean.npy').mean(1).mean(1) #loading the mean file
img = cv2.imread(EXAMPLES_BASE_DIR+'data/images/nps_electric_guitar.png')
img=cv2.resize(img,dim)
img = img.astype(numpy.float32)
img[:,:,0] = (img[:,:,0] - ilsvrc_mean[0])
img[:,:,1] = (img[:,:,1] - ilsvrc_mean[1])
img[:,:,2] = (img[:,:,2] - ilsvrc_mean[2])

# the below conversion is no longer needed, keeping it as an example of
# how to use RW_HOST_TENSOR_DESCRIPTOR

# Change the shape to match input expected by the hardware network.
# Specifically this will convert to planar format where the channels
# are sequential in memory rather than mixed together like they are for
# RGB or BGR format.  This format is BBBBGGGGRRRR
img = numpy.swapaxes(img, 0, 2)
img = numpy.swapaxes(img, 1, 2)

host_tensor_descriptor = fifoIn.get_option(mvnc.FifoOption.RO_GRAPH_TENSOR_DESCRIPTOR)
#create host tensor descriptor, layout CHW, FP32
host_tensor_descriptor.dataType = mvnc.FifoDataType.FP32.value
host_tensor_descriptor.wStride = 4 #FP32
host_tensor_descriptor.hStride = host_tensor_descriptor.wStride * host_tensor_descriptor.w
host_tensor_descriptor.cStride = host_tensor_descriptor.hStride * host_tensor_descriptor.h
host_tensor_descriptor.totalSize = host_tensor_descriptor.cStride * host_tensor_descriptor.c
fifoIn.set_option(mvnc.FifoOption.RW_HOST_TENSOR_DESCRIPTOR, host_tensor_descriptor)

# ***************************************************************
# Send the image to the NCS
# ***************************************************************
graph.queue_inference_with_fifo_elem(fifoIn, fifoOut, img, 'user object')

# ***************************************************************
# Get the result from the NCS
# ***************************************************************
output, userobj = fifoOut.read_elem()

# ***************************************************************
# Print the results of the inference form the NCS
# ***************************************************************
order = output.argsort()[::-1][:6]
print('\n------- predictions --------')
for i in range(0,5):
	print ('prediction ' + str(i) + ' (probability ' + str(output[order[i]]) + ') is ' + labels[order[i]] + '  label index is: ' + str(order[i]) )


# ***************************************************************
# Clean up the graph and the device
# ***************************************************************
fifoIn.destroy()
fifoOut.destroy()
graph.destroy()
device.close()
    



