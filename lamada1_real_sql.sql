CREATE DATABASE IF NOT EXISTS news_db
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_general_ci;

USE news_db;

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

CREATE TABLE IF NOT EXISTS news_ai_meta (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id INT NOT NULL,
    summary TEXT NOT NULL,
    topic VARCHAR(200) NOT NULL,
    keywords VARCHAR(500) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_news_meta_article
      FOREIGN KEY (article_id) REFERENCES news_articles(id)
      ON DELETE CASCADE
);


