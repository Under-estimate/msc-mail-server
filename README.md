## MSC 邮件服务器项目

### 现在可以公开的情报
#### MySQL数据表
> 用户表(users)
> | 列名 | 类型 |
> | -- | -- |
> | username | VARCHAR(64) |
> | password | CHAR(32) **MD5加密** |


> 邮件表(mails)
> | 列名 | 类型 |
> | -- | -- | 
> | uid | CHAR(36) **通过UUID()函数生成** |
> | sender | VARCHAR(64) |
> | receiver | VARCHAR(64) |
> | create_time | DATETIME **默认NOW()** |
> | content | TEXT |