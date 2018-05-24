SHELL := /bin/bash
PATH := $(PATH):$(HOME)/bin

test:
	grow install example
	grow preprocess
	grow build example
