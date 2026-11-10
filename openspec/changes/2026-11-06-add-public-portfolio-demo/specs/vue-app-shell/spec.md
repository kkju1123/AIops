# vue-app-shell Delta Specification

## MODIFIED Requirements

### Requirement: Root route behavior

Vue 应用 SHALL 将根路由作为公开项目入口，同时保留工作台的全屏应用外壳。

#### Scenario: Anonymous root navigation

- **WHEN** 匿名访客访问 `/`
- **THEN** 应用 MUST 展示公开项目介绍页，而不是自动跳转到登录页。

#### Scenario: Authenticated workspace navigation

- **WHEN** 已认证用户访问真实工作台路由
- **THEN** 应用 MUST 继续在现有全屏工作台外壳中渲染对应模块。
