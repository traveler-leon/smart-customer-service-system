#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
运行Text2SQL模块的测试套件
"""

import sys
import os
import argparse

# 确保能正确导入项目模块
sys.path.insert(0, os.path.abspath('.'))

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='运行Text2SQL模块测试')
    parser.add_argument('--tests', nargs='+', help='要运行的特定测试，例如: test_ask test_train')
    parser.add_argument('--skip', nargs='+', help='要跳过的测试，例如: test_embedding_generation')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    args = parser.parse_args()
    
    print("开始运行Text2SQL模块测试...")
    
    # 导入测试模块
    from tests.test_text2sql_comprehensive import Text2SQLTestCase, run_tests
    
    # 如果指定了特定测试
    if args.tests:
        # 导入运行指定测试的功能
        import unittest
        import asyncio
        
        # 设置测试套件
        suite = unittest.TestSuite()
        
        # 先添加同步测试
        if 'test_create_instance' in args.tests:
            suite.addTest(Text2SQLTestCase('test_create_instance'))
        
        # 运行测试套件
        if suite.countTestCases() > 0:
            unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
        
        # 运行异步测试
        async_tests = []
        all_async_tests = [
            'test_generate_sql',
            'test_embedding_generation',
            'test_vector_store_retrieval',
            'test_middleware',
            'test_run_sql',
            'test_ask',
            'test_train'
        ]
        
        for test in all_async_tests:
            if test in args.tests:
                async_tests.append(test)
        
        print(f"将运行以下异步测试: {async_tests}")
        
        # 从test_text2sql_comprehensive.py导入运行单个异步测试的功能
        from tests.test_text2sql_comprehensive import run_async_test
        
        loop = asyncio.get_event_loop()
        for test_name in async_tests:
            print(f"\n{'=' * 50}")
            print(f"运行测试: {test_name}")
            print(f"{'=' * 50}")
            loop.run_until_complete(run_async_test(test_name))
    elif args.skip:
        # 修改test_text2sql_comprehensive.py中的run_tests函数
        import unittest
        import asyncio
        
        # 设置测试套件
        suite = unittest.TestSuite()
        
        # 添加同步测试(如果不在skip列表中)
        if 'test_create_instance' not in args.skip:
            suite.addTest(Text2SQLTestCase('test_create_instance'))
        
        # 运行测试套件
        if suite.countTestCases() > 0:
            unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
        
        # 运行异步测试
        async_tests = []
        all_async_tests = [
            'test_generate_sql',
            'test_embedding_generation',
            'test_vector_store_retrieval',
            'test_middleware',
            'test_run_sql',
            'test_ask',
            'test_train'
        ]
        
        for test in all_async_tests:
            if test not in args.skip:
                async_tests.append(test)
        
        print(f"将运行以下异步测试: {async_tests}")
        
        # 从test_text2sql_comprehensive.py导入运行单个异步测试的功能
        from tests.test_text2sql_comprehensive import run_async_test
        
        loop = asyncio.get_event_loop()
        for test_name in async_tests:
            print(f"\n{'=' * 50}")
            print(f"运行测试: {test_name}")
            print(f"{'=' * 50}")
            loop.run_until_complete(run_async_test(test_name))
    else:
        # 默认运行所有测试
        run_tests()
    
    print("测试完成!")

if __name__ == "__main__":
    main() 