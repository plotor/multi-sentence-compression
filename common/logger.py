# -*- coding: utf8 -*-

import logging

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
    datefmt='%a, %d %b %Y %H:%M:%S',
    filename='E:/PythonWorkspace/logs/event_msc.log',
    filemode='w')