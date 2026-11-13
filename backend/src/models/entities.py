from dataclasses import dataclass,field
from typing import Any
@dataclass
class FiducialDataset:
 id:str
 name:str
 source:str
 points:list[dict]
 created_at:str=''
@dataclass
class FrameSpec:
 id:str
 name:str
 dataset_id:str
 source_frame:str
 target_frame:str
 unit:str
 axes:str
 created_at:str=''
@dataclass
class RegistrationStudy:
 id:str
 name:str
 dataset_id:str
 frame_id:str
 threshold_mm:float
 iterations:int
 seed:int
 snapshot:dict
 checksum:str
 created_at:str=''
@dataclass
class RegistrationRun:
 id:str
 study_id:str
 status:str='queued'
 result:dict[str,Any]=field(default_factory=dict)
 error:str=''
 created_at:str=''
@dataclass
class ReviewDecision:
 id:str
 action:str
 comment:str
 actor:str
 created_at:str=''
@dataclass
class AlignmentReview:
 id:str
 run_id:str
 comment:str
 status:str='pending'
 reviewer:str=''
 created_at:str=''
 # 每次复核决定（批准/退回/撤销）均追加留痕，不覆盖历史
 decisions:list[dict]=field(default_factory=list)
 # 当前有效批准对应的决定 id；撤销后清空，重新批准指向新决定
 effective_decision_id:str=''
 # 撤销原因（撤销动作本身与原因同步保存在 decisions 中）
 revoked_reason:str=''
@dataclass
class Report:
 id:str
 run_id:str
 review_id:str
 title:str
 created_at:str=''
 # 报告生成时绑定的复核决定 id，页面可追查报告对应哪次决定
 decision_id:str=''
 # active=可下载；其绑定批准被撤销后置 invalid，永不因再次批准恢复
 status:str='active'
 invalid_reason:str=''
