CREATE TABLE IF NOT EXISTS news_articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(500) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content LONGTEXT NOT NULL,
    article_date DATETIME NULL,
    source VARCHAR(100) NOT NULL,
    category VARCHAR(100) NULL,
    is_summarized TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_news_url UNIQUE (url)
);

use news_db;
show tables;

SHOW COLUMNS FROM news_ai_meta;


DESC news_ai_meta;

-- id : 내부 PK (AUTO_INCREMENT)
