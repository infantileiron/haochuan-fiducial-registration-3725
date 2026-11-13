-- 002 复核决定留痕、撤销批准与报告失效
-- 本工程表结构为通用 (id TEXT, payload TEXT) JSON 载荷，无新增列/表，
-- 结构升级在应用启动时由 src/services/migration.py 幂等完成：
--   1) reviews.payload 增补 decisions（每次批准/退回/撤销决定，含经办人、原因、时间）、
--      effective_decision_id（当前有效批准决定）、revoked_reason（撤销原因）；
--   2) reports.payload 增补 decision_id（生成时绑定的批准决定）、
--      status(active/invalid)、invalid_reason；
--   3) 旧数据原有复核意见与报告完整保留、仍可查阅；历史批准报告默认保持 active。
-- 本文件仅为变更说明，实际升级逻辑见 migration.py，无需手工执行 DDL。
SELECT 1;
