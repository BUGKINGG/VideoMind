-- ==========================================
-- VideoMind Database Schema
-- 执行方式: 在 MySQL 中运行 source schema.sql;
-- ==========================================

CREATE DATABASE IF NOT EXISTS `video_mind` 
    DEFAULT CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE `video_mind`;

-- 先关闭外键检查，避免 DROP/CREATE 顺序报错
SET FOREIGN_KEY_CHECKS = 0;

-- 清理旧表（如不存在则忽略）
DROP TABLE IF EXISTS `subtitle`;
DROP TABLE IF EXISTS `message`;
DROP TABLE IF EXISTS `conversation`;
DROP TABLE IF EXISTS `video`;
DROP TABLE IF EXISTS `user`;

-- ==========================================
-- 1. 用户表
-- ==========================================
CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户名',
  `phone` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '手机号（登录账号）',
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '加密后的密码',
  `avatar_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '头像URL',
  `cookie` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'B站Cookie（可选）',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ==========================================
-- 2. 视频表
-- ==========================================
CREATE TABLE `video` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '视频ID',
  `user_id` bigint NOT NULL COMMENT '上传/解析用户ID',
  `url` varchar(500) NOT NULL COMMENT '视频URL(B站)',
  `title` varchar(255) DEFAULT '' COMMENT '视频标题',
  `status` tinyint DEFAULT '0' COMMENT '0解析中 1完成 2失败',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `part` int DEFAULT '1' COMMENT '分P序号，默认1',
  `summary` text COMMENT 'AI总结内容',
  `subtitle_count` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_url_part` (`url`(255),`part`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='视频表';

-- ==========================================
-- 3. 会话表
-- ==========================================
CREATE TABLE `conversation` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `video_id` bigint DEFAULT NULL COMMENT '关联的视频解析任务，允许NULL（未来纯文本对话）',
  `title` varchar(255) DEFAULT NULL COMMENT '会话标题，默认用视频标题',
  `status` tinyint DEFAULT '0' COMMENT '0处理中 1完成 2失败',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `subtitle_count` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_user_updated` (`user_id`,`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='会话历史记录';

-- ==========================================
-- 4. 消息表
-- ==========================================
CREATE TABLE `message` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `conversation_id` bigint NOT NULL COMMENT '所属会话',
  `role` varchar(20) NOT NULL COMMENT 'user / ai / system',
  `content` text NOT NULL COMMENT '消息内容（AI存Markdown原文）',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_conversation_time` (`conversation_id`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='会话消息';

-- ==========================================
-- 5. 字幕表 (外键依赖 video 表)
-- ==========================================
CREATE TABLE `subtitle` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '字幕ID',
  `video_id` bigint NOT NULL COMMENT '关联视频ID',
  `start_at` double NOT NULL COMMENT '开始时间(秒)，如 12.345',
  `end_at` double NOT NULL COMMENT '结束时间(秒)，如 15.678',
  `content` text NOT NULL COMMENT '字幕内容',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_video_id` (`video_id`),
  KEY `idx_video_time` (`video_id`,`start_at`) COMMENT '按视频+时间查询字幕',
  CONSTRAINT `subtitle_ibfk_1` FOREIGN KEY (`video_id`) REFERENCES `video` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='字幕表';

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;