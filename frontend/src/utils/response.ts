// 对应 response.py 的结构

export type SystemMessageType = 'info' | 'warning' | 'success' | 'error';

import { AgentType } from './enum';


export interface BaseMessage {
  id: string;
  msg_type: 'system' | 'agent' | 'user' | 'tool' | 'progress' | 'stream';
  content?: string | null;
}

export interface ToolMessage extends BaseMessage {
  msg_type: 'tool';
  tool_name: 'execute_code' | 'search_scholar';
  input: Record<string, unknown> | null;
  output: string[] | OutputItem[] | null;
}

export interface SystemMessage extends BaseMessage {
  msg_type: 'system';
  type: SystemMessageType;
}

export interface UserMessage extends BaseMessage {
  msg_type: 'user';
}

export interface AgentMessage extends BaseMessage {
  msg_type: 'agent';
  agent_type: AgentType;
}

export interface ModelerMessage extends AgentMessage {
  agent_type: AgentType.MODELER;
}

export interface CoordinatorMessage extends AgentMessage {
  agent_type: AgentType.COORDINATOR;
}


// 代码执行结果类型
export type ExecutionFormat =
  | 'text'
  | 'html'
  | 'markdown'
  | 'png'
  | 'jpeg'
  | 'svg'
  | 'pdf'
  | 'latex'
  | 'json'
  | 'javascript';

export interface BaseCodeExecution {
  res_type: 'stdout' | 'stderr' | 'result' | 'error';
  msg?: string;
}

export interface StdOutExecution extends BaseCodeExecution {
  res_type: 'stdout';
}

export interface StdErrExecution extends BaseCodeExecution {
  res_type: 'stderr';
}

export interface ResultExecution extends BaseCodeExecution {
  res_type: 'result';
  format: ExecutionFormat;
}

export interface ErrorExecution extends BaseCodeExecution {
  res_type: 'error';
  name: string;
  value: string;
  traceback: string;
}

export type OutputItem = StdOutExecution | StdErrExecution | ResultExecution | ErrorExecution;

export interface ScholarMessage extends ToolMessage {
  tool_name: 'search_scholar';
  input: Record<string, unknown>;
  output: string[];
}

export interface InterpreterMessage extends ToolMessage {
  tool_name: 'execute_code';
  input: {
    code: string;
  } | null;
  output: OutputItem[] | null;
}


export interface CoderMessage extends AgentMessage {
  agent_type: AgentType.CODER;
}

export interface WriterMessage extends AgentMessage {
  agent_type: AgentType.WRITER;
  sub_title?: string;
}

export interface ReviewerMessage extends AgentMessage {
  agent_type: AgentType.REVIEWER;
  review_score?: number;
  dimension_scores?: Record<string, number>;
}

export interface AnalyzerMessage extends AgentMessage {
  agent_type: AgentType.ANALYZER;
}

export interface ValidatorMessage extends AgentMessage {
  agent_type: AgentType.VALIDATOR;
}

export interface OptimizerMessage extends AgentMessage {
  agent_type: AgentType.OPTIMIZER;
}

export interface ProgressMessage extends BaseMessage {
  msg_type: 'progress';
  type: SystemMessageType;
  percent: number;
  phase: string;
  message: string;
  elapsed_time?: number;
  sub_phase?: string;
  iteration?: number;
  max_iterations?: number;
  quality_score?: number;
}

export interface TaskStatusMessage {
  id: string;
  msg_type: 'task_status';
  content?: string | null;
  status: string;
  phase?: string;
  error?: string;
}

export interface StreamMessage extends BaseMessage {
  msg_type: 'stream';
  agent_type: string;
  delta: string;
  message_id: string;
  done: boolean;
}

export type Message = SystemMessage | ProgressMessage | UserMessage | CoderMessage | WriterMessage | ModelerMessage | CoordinatorMessage | ReviewerMessage | AnalyzerMessage | ValidatorMessage | OptimizerMessage | ToolMessage | StreamMessage;