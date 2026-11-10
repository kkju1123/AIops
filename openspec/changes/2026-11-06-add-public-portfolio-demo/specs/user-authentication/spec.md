# user-authentication Delta Specification

## MODIFIED Requirements

### Requirement: Frontend authentication experience

前端 SHALL 支持登录、注册、注销和持久化认证，同时允许匿名访问明确声明的公开项目页面。

#### Scenario: Anonymous visitor explores the public preview

- **WHEN** 未认证访客访问 `/` 或 `/demo`
- **THEN** 前端 MUST 允许访问且 MUST NOT 为展示导览而创建或共享认证身份。

#### Scenario: Anonymous visitor requests the real workspace

- **WHEN** 未认证访客访问受保护工作台路由
- **THEN** 前端 MUST 跳转到登录页并保留目标路径。
