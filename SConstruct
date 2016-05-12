# Code in this file originally from the mjmech project: https://github.com/mjbots/mjmech
#
# Copyright 2014-2015 Josh Pieper, jjp@pobox.com.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Additional modifications:
#
# Copyright 2016 Sam Creasey, sammy@sammy.net.  All rights reserved.

env = Environment()

# Set up our global environment.
if ARGUMENTS.get('debug', 0):
    env.Append(CPPFLAGS=['-O0'])
else:
    env.Append(CPPFLAGS=['-O3'])

# TODO sammy remove most of this if we don't have much C++
env.Append(CPPPATH=['#/'])
env.Append(CPPFLAGS=['-Wall', '-Werror', '-g', '-std=c++1y'])
env.Append(LINKFLAGS=['-rdynamic'])

canonenv = env
Export('canonenv')

import os
variant_suffix = '-' + os.uname()[4]

subdirs = ['src']

for subdir in subdirs:
    SConscript(subdir + '/SConscript',
               variant_dir=subdir + '/build' + variant_suffix,
               duplicate=0)
