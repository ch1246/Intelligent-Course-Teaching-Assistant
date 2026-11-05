-- ============================================================
-- 手工索引脚本（手写 DDL，不走 Django 迁移）
-- 目标库：MySQL 8.0 / InnoDB / utf8mb4 / teek_teaching_assistant
-- 目的：补齐 Django 隐式索引覆盖不到的热点查询 —— 即
--       "等值过滤 + ORDER BY 排序" 这类需要复合索引才能同时消除
--       回表与 filesort 的查询形状。
--
-- 执行：mysql -h127.0.0.1 -uroot teek_teaching_assistant < backend/sql/hot_path_indexes.sql
-- 说明：显式声明 ALGORITHM=INPLACE, LOCK=NONE —— 二级索引创建走在线 DDL，
--       不阻塞并发读写；若服务端无法满足会直接报错而不会静默锁表。
-- 注意：本文件产生的索引 Django ORM 不感知（models.py 与数据库会存在漂移），
--       必须与本文件配套维护；反之，若改用 Meta.indexes + 迁移，请删除本文件。
-- ============================================================

-- 1) 管理端用户列表：WHERE role = ? AND is_approved = ? ORDER BY date_joined DESC
--    等值前缀 (role, is_approved) + 有序尾列 date_joined，可走反向索引扫描，消除 filesort。
CREATE INDEX idx_user_role_approved_joined
    ON accounts_user (role, is_approved, date_joined)
    ALGORITHM=INPLACE LOCK=NONE;

-- 2) 会话历史：WHERE session_id = ? ORDER BY created_at DESC
--    替代原来的 "外键单列索引 + filesort"。
CREATE INDEX idx_chat_message_session_created
    ON chat_message (session_id, created_at)
    ALGORITHM=INPLACE LOCK=NONE;

-- 3) 我的会话 / 课程会话列表：WHERE user_id = ? AND course_id = ? ORDER BY updated_at DESC
CREATE INDEX idx_chat_session_user_course_updated
    ON chat_session (user_id, course_id, updated_at)
    ALGORITHM=INPLACE LOCK=NONE;

-- 4) 链路追踪：WHERE session_id = ? ORDER BY created_at DESC
--    （全局按时间倒序的列表查询用 (created_at) 更合适，两种形状按实际访问占比取舍。）
CREATE INDEX idx_trace_session_created
    ON trace_log (session_id, created_at)
    ALGORITHM=INPLACE LOCK=NONE;

-- ============================================================
-- 回滚脚本
-- ============================================================
-- DROP INDEX idx_user_role_approved_joined        ON accounts_user;
-- DROP INDEX idx_chat_message_session_created     ON chat_message;
-- DROP INDEX idx_chat_session_user_course_updated ON chat_session;
-- DROP INDEX idx_trace_session_created            ON trace_log;
