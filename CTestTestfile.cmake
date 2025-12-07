# CMake generated Testfile for 
# Source directory: /home/dp012/Desktop/gitmacbranch/mako-pr
# Build directory: /home/dp012/Desktop/gitmacbranch/mako-pr
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(test_marshal "/home/dp012/Desktop/gitmacbranch/mako-pr/test_marshal")
set_tests_properties(test_marshal PROPERTIES  _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;916;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(test_rpc "/home/dp012/Desktop/gitmacbranch/mako-pr/test_rpc")
set_tests_properties(test_rpc PROPERTIES  _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;923;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(test_future "/home/dp012/Desktop/gitmacbranch/mako-pr/test_future")
set_tests_properties(test_future PROPERTIES  _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;937;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(test_reactor "/home/dp012/Desktop/gitmacbranch/mako-pr/test_reactor")
set_tests_properties(test_reactor PROPERTIES  _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;944;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(test_coroutine "/home/dp012/Desktop/gitmacbranch/mako-pr/test_coroutine")
set_tests_properties(test_coroutine PROPERTIES  _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;952;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(test_rpc_extended "/home/dp012/Desktop/gitmacbranch/mako-pr/test_rpc_extended")
set_tests_properties(test_rpc_extended PROPERTIES  _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;960;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(test_reactor_extended "/home/dp012/Desktop/gitmacbranch/mako-pr/test_reactor_extended")
set_tests_properties(test_reactor_extended PROPERTIES  _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;967;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(test_timeout_race "/home/dp012/Desktop/gitmacbranch/mako-pr/test_timeout_race")
set_tests_properties(test_timeout_race PROPERTIES  _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;974;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(test_and_event "/home/dp012/Desktop/gitmacbranch/mako-pr/test_and_event")
set_tests_properties(test_and_event PROPERTIES  _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;981;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(test_deterministic "/home/dp012/Desktop/gitmacbranch/mako-pr/test_deterministic")
set_tests_properties(test_deterministic PROPERTIES  _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;988;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(simpleTransaction "/home/dp012/Desktop/gitmacbranch/mako-pr/simpleTransaction")
set_tests_properties(simpleTransaction PROPERTIES  _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;991;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(simplePaxos "bash" "-c" "bash ./src/mako/update_config.sh && bash ./examples/simplePaxos.sh")
set_tests_properties(simplePaxos PROPERTIES  WORKING_DIRECTORY "/home/dp012/Desktop/gitmacbranch/mako-pr" _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;994;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
add_test(shard1ReplicationSimple "bash" "-c" "bash ./examples/test_1shard_replication_simple.sh")
set_tests_properties(shard1ReplicationSimple PROPERTIES  WORKING_DIRECTORY "/home/dp012/Desktop/gitmacbranch/mako-pr" _BACKTRACE_TRIPLES "/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;1000;add_test;/home/dp012/Desktop/gitmacbranch/mako-pr/CMakeLists.txt;0;")
subdirs("third-party/erpc")
