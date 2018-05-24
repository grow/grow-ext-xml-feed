SHELL := /bin/bash
PATH := $(PATH):$(HOME)/bin

test:
	grow install example
	grow preprocess example
	grow build example
