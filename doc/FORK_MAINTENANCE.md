# 门锁事件补丁与更新方式

本 fork 基于上游 `v0.5.0`，首个补丁版本为 `v0.5.0+loock.1`。

## 事件映射

仅修改 `loock.lock.t1` 的门服务 `siid=5`、事件 `eiid=1`。
按事件参数 `piid=2` 的原始代码设置 Home Assistant 的 `event_type`：

| 原始代码 | event_type |
| --- | --- |
| 1 | 关门 |
| 2 | 开门超时 |
| 4 | 门被破坏 |
| 5 | 门卡住 |
| 未知代码或缺少参数 | 原有的“发生异常”事件 |

保留原始参数、现有实体 ID 和 unique ID。参数通过 MIoT 属性 ID 定位，
不依赖中文字段名；新增事件类型使用上述中文名称。
实体显示名称为“门状态事件”。历史事件不改写，重启后恢复的旧事件也不伪造为新事件。

该补丁不会修改 sensor 值，不会从开锁事件推断物理开门，也不会推断锁舌状态。
匹配旧 `event_type: 发生异常` 的自动化应调整为所需的新事件类型。

## 安装和 HACS 更新来源

HACS 自定义仓库使用：

```text
huahuahuahuahuahuahuahua/ha_xiaomi_home
```

分类为 Integration。不要同时把 `XiaoMi/ha_xiaomi_home` 作为已安装仓库管理：
两个仓库安装到同一 `custom_components/xiaomi_home` 目录，上游安装会覆盖补丁。
移除上游的 HACS 跟踪记录时，不要选择卸载集成或删除小米账号配置。

此 fork 默认分支 `main` 包含补丁。HACS 从 fork 的发布版本更新。
版本后缀 `+loock.N` 用来区分上游版本和本地补丁版本。

## 合并上游更新

本地仓库的 `origin` 指向本 fork，`upstream` 指向 XiaoMi 官方仓库。
更新时合并上游，保留本 fork 的提交，避免将 `main` 重置为上游。

```sh
git fetch upstream
git switch main
git merge upstream/main
```

若有冲突，重点检查 `custom_components/xiaomi_home/event.py`，确保事件映射仍在。
合并后将 manifest 的版本调整为新上游版本加 `+loock.N`，运行原有测试和门锁回归测试，
提交时附加 `Co-authored-by: Codex <noreply@openai.com>`。
推送到本 fork，创建与 manifest 一致的新 tag 和 GitHub release，最后通过 HACS 更新。
不要直接安装上游 release，也不要使用会丢弃本 fork 提交的强制同步。

门锁回归测试需在安装了 Home Assistant 及集成依赖的 Python 环境运行：

```sh
python -m unittest discover -s test -p lock_event_mapping.py -v
```

测试用独立实体验证参数解析和 Event 类型校验，不向运行中的 HA 注入事件，
不控制真实门锁。部署后仍应通过真实开关门操作确认接收链路。
