#!/usr/bin/env python3
"""恢复 XGO 默认腿模式：enable_wheel_control(0)。

调用时机：机器来电后第一件事（见 docs/technical/2026-08-16-main-flow-debug.md §4-1）。
若 F 测试（锁轮/轮控）把固件留在 wheel 模式，主流程 move_x 会全部失效、
狗原地转圈无法前进；本脚本把固件切回默认腿模式。

前置：串口空闲（手控/原厂服务未占用 /dev/ttyAMA0），或经手控服务 HTTP
等效执行（{"kind":"wheel","enabled":false,"speeds":[0,0,0,0]}）。
"""

from uiutils import dog

dog.enable_wheel_control(0)
print("wheel control disabled; foot mode restored", flush=True)
