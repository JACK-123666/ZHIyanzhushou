-- clip_trends/sql/schema.sql
-- 剪辑趋势爬虫系统 - 数据库建表脚本

CREATE DATABASE IF NOT EXISTS clip_trends
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE clip_trends;

-- 4.1 分类体系元数据表
CREATE TABLE technique_taxonomy (
    id INT PRIMARY KEY AUTO_INCREMENT,
    dimension VARCHAR(20) NOT NULL,
    category VARCHAR(30) NOT NULL,
    subcategory VARCHAR(40) NOT NULL,
    detail TEXT,
    keywords JSON NOT NULL,
    weight DECIMAL(3,2) DEFAULT 1.00,
    UNIQUE KEY uk_dim_cat_sub (dimension, category, subcategory)
) ENGINE=InnoDB;

-- 4.2 爬取视频表
CREATE TABLE videos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    site VARCHAR(20) NOT NULL,
    source_url VARCHAR(500) NOT NULL,
    source_id VARCHAR(100) NOT NULL,
    title VARCHAR(300),
    thumbnail_url VARCHAR(500),
    duration_sec DECIMAL(8,2),
    resolution VARCHAR(20),
    tags_json JSON,
    description TEXT,
    popularity_score DECIMAL(10,2) DEFAULT 0,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_site_source (site, source_id),
    INDEX idx_site (site),
    INDEX idx_popularity (popularity_score DESC),
    INDEX idx_crawled_at (crawled_at)
) ENGINE=InnoDB;

-- 4.3 视频技法桥表
CREATE TABLE video_techniques (
    id INT PRIMARY KEY AUTO_INCREMENT,
    video_id INT NOT NULL,
    taxonomy_id INT NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 0.70,
    evidence TEXT,
    method ENUM('rule','llm','qwen-vl','hybrid') DEFAULT 'rule',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_video_taxonomy (video_id, taxonomy_id),
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    FOREIGN KEY (taxonomy_id) REFERENCES technique_taxonomy(id) ON DELETE CASCADE,
    INDEX idx_taxonomy (taxonomy_id),
    INDEX idx_method (method)
) ENGINE=InnoDB;

-- 4.4 每日趋势快照表
CREATE TABLE daily_trends (
    id INT PRIMARY KEY AUTO_INCREMENT,
    date DATE NOT NULL,
    taxonomy_id INT NOT NULL,
    video_count INT DEFAULT 0,
    avg_popularity DECIMAL(10,2) DEFAULT 0,
    avg_duration DECIMAL(8,2),
    sample_video_ids JSON,
    trending_direction ENUM('rising','stable','declining') DEFAULT 'stable',
    UNIQUE KEY uk_date_taxonomy (date, taxonomy_id),
    FOREIGN KEY (taxonomy_id) REFERENCES technique_taxonomy(id) ON DELETE CASCADE,
    INDEX idx_date (date),
    INDEX idx_trending (trending_direction)
) ENGINE=InnoDB;

-- 4.5 爬取日志表
CREATE TABLE crawl_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    site VARCHAR(20) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    videos_total INT DEFAULT 0,
    videos_new INT DEFAULT 0,
    errors TEXT,
    status ENUM('running','success','partial','failed') DEFAULT 'running',
    INDEX idx_site (site)
) ENGINE=InnoDB;

-- 4.6 剪辑模板表
CREATE TABLE editing_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    taxonomy_ids_json JSON NOT NULL,
    prompt_snippet TEXT NOT NULL,
    use_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
