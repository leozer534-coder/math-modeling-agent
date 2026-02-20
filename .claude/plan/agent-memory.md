# Agent 记忆系统集成计划

## 任务概述
将 MemoryManager 集成到 Agent 基类，实现跨会话学习能力。

## 执行状态
- [x] 创建目录结构
- [ ] 重构 Agent 基类
- [ ] 更新 CoderAgent
- [ ] 更新 ModelerAgent
- [ ] 测试验证

## 设计决策

### 1. 记忆初始化策略
- 延迟初始化：首次使用时创建 MemoryManager
- 可选启用：通过 `enable_memory` 参数控制

### 2. 经验增强流程
```
run() 调用前:
  1. _recall_experience() - 回忆相关经验
  2. _enhance_prompt_with_experience() - 增强 prompt

run() 调用后:
  1. _evaluate_result() - 评估结果质量
  2. _save_task_experience() - 保存经验
```

### 3. 记忆存储路径
- 长期记忆: `backend/data/memory/long_term/`
- 情景记忆: `backend/data/memory/episodic/`

## 关键代码变更

### agent.py
- 新增 MemoryManager 属性
- 新增经验回忆方法
- 新增经验保存方法
- 新增结果评估方法

### coder_agent.py
- 利用历史错误经验避免重复错误
- 保存代码执行经验

### modeler_agent.py
- 利用历史建模经验推荐模型
- 保存建模方案经验

## 预期收益
1. 跨会话学习：从历史任务中学习
2. 错误预防：避免重复已知错误
3. 模型推荐：基于成功案例推荐模型
4. 经验积累：持续改进任务执行质量
