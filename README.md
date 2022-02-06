## MSC 邮件服务器项目

### 现在可以公开的情报
#### MySQL数据表
> 用户表(users)
> | 列名 | 类型 | 说明 |
> | -- | -- | -- |
> | username | VARCHAR(64) | 不包含@msc.com |
> | password | CHAR(32) | MD5加密 |


> 邮件表(mails)
> | 列名 | 类型 | 说明 |
> | -- | -- |  -- |
> | uid | CHAR(36) | 通过UUID()函数生成 |
> | sender | VARCHAR(64) | 包含@msc.com |
> | receiver | VARCHAR(64) | 包含@msc.com |
> | create_time | DATETIME | 默认NOW() |
> | content | TEXT | |