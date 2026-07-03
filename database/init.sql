-- ============================================
-- QuickOJ 数据库初始化脚本
-- 目标: SQL Server
-- ============================================

 -- 创建数据库（如不存在则需手动创建）
 CREATE DATABASE OJPlatform;
 GO
 USE OJPlatform;
 GO

-- ============================================
-- 1. Users 表
-- ============================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Users' AND xtype='U')
CREATE TABLE Users (
    user_id          BIGINT IDENTITY(1,1) PRIMARY KEY,
    username         VARCHAR(30)    NOT NULL,
    password_hash    VARCHAR(255)   NOT NULL,
    role             VARCHAR(20)    NOT NULL DEFAULT 'user'
                        CONSTRAINT CK_Users_role CHECK (role IN ('root','admin','user')),
    status           VARCHAR(20)    NOT NULL DEFAULT 'active'
                        CONSTRAINT CK_Users_status CHECK (status IN ('active','banned')),
    email            VARCHAR(100)   NULL,
    avatar           VARCHAR(255)   NULL,
    solved_problems  INT            NOT NULL DEFAULT 0,
    total_submissions INT           NOT NULL DEFAULT 0,
    token_version    INT            NOT NULL DEFAULT 0,
    registered_at    DATETIME       NOT NULL DEFAULT GETDATE(),
    last_login       DATETIME       NULL,

    CONSTRAINT UQ_Users_username UNIQUE (username)
);
GO

-- ============================================
-- 2. Tags 表
-- ============================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Tags' AND xtype='U')
CREATE TABLE Tags (
    tag_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
    tag_name    NVARCHAR(50)  NOT NULL,
    description NVARCHAR(500) NULL,
    problems    BIGINT        NOT NULL DEFAULT 0,

    CONSTRAINT UQ_Tags_tag_name UNIQUE (tag_name)
);
GO

-- ============================================
-- 3. Problems 表
-- ============================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Problems' AND xtype='U')
CREATE TABLE Problems (
    problem_id                   BIGINT IDENTITY(1,1) PRIMARY KEY,
    problem_number               BIGINT        NULL,
    uploader_id                  BIGINT        NOT NULL
                                    REFERENCES Users(user_id),
    problem_status               VARCHAR(20)   NOT NULL DEFAULT 'pending_new'
                                    CONSTRAINT CK_Problems_status CHECK (problem_status IN
                                        ('pending_new','pending_modify','approved','rejected','archived','frozen')),
    problem_name                 NVARCHAR(50)  NOT NULL,
    difficulty                   INT           NOT NULL,
    statement                    NVARCHAR(MAX) NOT NULL,
    problem_type                 VARCHAR(20)   NOT NULL
                                    CONSTRAINT CK_Problems_type CHECK (problem_type IN
                                        ('traditional','interactive','output-only','communication')),
    time_limit                   INT           NOT NULL,       -- 单位 ms
    memory_limit                 INT           NOT NULL,       -- 单位 KB
    accepted_user_count          INT           NOT NULL DEFAULT 0,
    submissions_before_accepted  INT           NOT NULL DEFAULT 0,
    source                       NVARCHAR(100) NULL,
    sample_download_policy       VARCHAR(20)   NOT NULL DEFAULT 'none'
                                    CONSTRAINT CK_Problems_download CHECK (sample_download_policy IN
                                        ('all','none','first_failed')),
    created_at                   DATETIME      NOT NULL DEFAULT GETDATE(),
    updated_at                   DATETIME      NULL,
    reviewer_id                  BIGINT        NULL REFERENCES Users(user_id),
    reviewed_at                  DATETIME      NULL,
    review_comment               NVARCHAR(500) NULL,

    CONSTRAINT UQ_Problems_number UNIQUE (problem_number)
);
GO

-- ============================================
-- 4. TagProblems 关联表
-- ============================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='TagProblems' AND xtype='U')
CREATE TABLE TagProblems (
    tag_id     BIGINT NOT NULL REFERENCES Tags(tag_id),
    problem_id BIGINT NOT NULL REFERENCES Problems(problem_id),
    PRIMARY KEY (tag_id, problem_id)
);
GO

-- ============================================
-- 5. Submissions 表
-- ============================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Submissions' AND xtype='U')
CREATE TABLE Submissions (
    submission_id  BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id        BIGINT         NOT NULL,
    username       NVARCHAR(50)   NULL,
    problem_id     BIGINT         NOT NULL,
    problem_number BIGINT         NULL,
    problem_name   NVARCHAR(50)   NULL,
    problem_type   VARCHAR(20)    NOT NULL,
    is_test_run    BIT            NOT NULL DEFAULT 0,
    code           NVARCHAR(MAX)  NOT NULL,
    code_length    INT            NOT NULL,
    language       VARCHAR(20)    NOT NULL,
    status         VARCHAR(20)    NOT NULL DEFAULT 'pending',
    run_time       INT            NULL,
    run_memory     INT            NULL,
    judged_result  NVARCHAR(MAX)  NULL,
    submitted_at   DATETIME       NOT NULL DEFAULT GETDATE(),
    judged_at      DATETIME       NULL
);
GO

-- ============================================
-- 6. UserAcceptedProblems 表
-- ============================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='UserAcceptedProblems' AND xtype='U')
CREATE TABLE UserAcceptedProblems (
    id                BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id           BIGINT   NOT NULL REFERENCES Users(user_id),
    problem_id        BIGINT   NOT NULL REFERENCES Problems(problem_id),
    first_accepted_at DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT UQ_UserAccepted UNIQUE (user_id, problem_id)
);
GO

-- ============================================
-- 7. Notifications 表
-- ============================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Notifications' AND xtype='U')
CREATE TABLE Notifications (
    notification_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id         BIGINT        NULL REFERENCES Users(user_id),
    title           NVARCHAR(100) NOT NULL,
    content         NVARCHAR(500) NOT NULL,
    is_read         BIT           NOT NULL DEFAULT 0,
    created_at      DATETIME      NOT NULL DEFAULT GETDATE()
);
GO

-- ============================================
-- 索引
-- ============================================

-- Users 索引
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_users_role')
    CREATE INDEX idx_users_role ON Users(role);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_users_status')
    CREATE INDEX idx_users_status ON Users(status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_users_solved')
    CREATE INDEX idx_users_solved ON Users(solved_problems DESC);

-- Problems 索引
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_problems_status')
    CREATE INDEX idx_problems_status ON Problems(problem_status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_problems_uploader')
    CREATE INDEX idx_problems_uploader ON Problems(uploader_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_problems_number')
    CREATE INDEX idx_problems_number ON Problems(problem_number) WHERE problem_number IS NOT NULL;
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_problems_accepted_count')
    CREATE INDEX idx_problems_accepted_count ON Problems(accepted_user_count DESC);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_problems_updated')
    CREATE INDEX idx_problems_updated ON Problems(updated_at);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_problems_created')
    CREATE INDEX idx_problems_created ON Problems(created_at DESC);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_problems_difficulty')
    CREATE INDEX idx_problems_difficulty ON Problems(difficulty);

-- TagProblems 索引
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_tagproblems_problem')
    CREATE INDEX idx_tagproblems_problem ON TagProblems(problem_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_tagproblems_tag')
    CREATE INDEX idx_tagproblems_tag ON TagProblems(tag_id);

-- Submissions 索引
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_submissions_user')
    CREATE INDEX idx_submissions_user ON Submissions(user_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_submissions_problem')
    CREATE INDEX idx_submissions_problem ON Submissions(problem_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_submissions_status')
    CREATE INDEX idx_submissions_status ON Submissions(status);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_submissions_time')
    CREATE INDEX idx_submissions_time ON Submissions(submitted_at DESC);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_submissions_list')
    CREATE INDEX idx_submissions_list ON Submissions(is_test_run, submitted_at DESC);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_submissions_pending')
    CREATE INDEX idx_submissions_pending ON Submissions(status, submitted_at) WHERE status = 'pending';
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_submissions_test')
    CREATE INDEX idx_submissions_test ON Submissions(is_test_run);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_submissions_pnum')
    CREATE INDEX idx_submissions_pnum ON Submissions(problem_number) WHERE problem_number > 0;
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_submissions_username')
    CREATE INDEX idx_submissions_username ON Submissions(username);

-- UserAcceptedProblems 索引
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_uap_user')
    CREATE INDEX idx_uap_user ON UserAcceptedProblems(user_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_uap_problem')
    CREATE INDEX idx_uap_problem ON UserAcceptedProblems(problem_id);

-- Notifications 索引
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_notif_user')
    CREATE INDEX idx_notif_user ON Notifications(user_id);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_notif_time')
    CREATE INDEX idx_notif_time ON Notifications(created_at DESC);

GO

-- ============================================
-- 视图
-- ============================================

-- 待审核题目队列
IF OBJECT_ID('v_review_queue', 'V') IS NOT NULL DROP VIEW v_review_queue;
GO
CREATE VIEW v_review_queue AS
SELECT problem_id, problem_number, problem_name, problem_status, difficulty,
       problem_type, uploader_id, updated_at, created_at
FROM Problems
WHERE problem_status IN ('pending_new', 'pending_modify');
GO

-- 用户已通过题目
IF OBJECT_ID('v_user_solved', 'V') IS NOT NULL DROP VIEW v_user_solved;
GO
CREATE VIEW v_user_solved AS
SELECT uap.user_id, uap.problem_id, uap.first_accepted_at,
       p.problem_number, p.problem_name, p.difficulty
FROM UserAcceptedProblems uap
JOIN Problems p ON p.problem_id = uap.problem_id;
GO

PRINT 'QuickOJ 数据库初始化完成！';
