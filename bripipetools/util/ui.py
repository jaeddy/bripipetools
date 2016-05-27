import os
import sys
import __builtin__

def prompt_raw(prompt_text):
    """
    Display prompt text and ask for raw input.
    """
    sys.stderr.write('{}\n'.format(prompt_text))
    return __builtin__.raw_input()

def list_options(option_list):
    """
    Display formatted list of objects in numbered order.
    """
    for idx, option in enumerate(option_list):
        print("%3d : %s" % (idx, option))

def input_to_int(input_func):
    """
    Collect input from function and convert to integer.
    """
    if len(input_func()):
        return int(input_func())

def input_to_int_list(input_func, sep=','):
    """
    Collect input from function, split based on separator, and convert to list
    of integers.
    """
    # input_str = input_func()
    return [int(i) for i in input_func().split(sep)]
