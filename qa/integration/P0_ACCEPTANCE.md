# P0 负责人验收

2026-10-22。判定：**中央建筑与一人合模技术样板通过；完整美术、人物精修、全场自由漫游不通过。**

本轮证明正式项目内的资产隔离、可编辑建筑生成、一名真实人物导入、固定构图比较和有限连续行走可以共同成立。它没有完成《雅典学院》完整复现。

## 可检查的交付

- [Windows 启动入口](../../unity/start-sample.cmd)，依赖完整 `unity/Builds/P0/` 目录。手动日志写入 `qa/environment/manual/player-latest.log`。
- [Unity 场景](../../unity/Assets/Scenes/ProductionSample.unity)、[建筑参数](../../art/environment/architecture-parameters.json)、[B 交接清单](../../art/characters/plato/v001/delivery.json)。
- [实际主视图](../environment/runs/20261022-214215-017/hero.png)、[近景](../environment/runs/20261022-214215-017/close.png)、[侧背](../environment/runs/20261022-214215-017/side.png)、[实际走到机位后的回望](../environment/runs/20261022-214215-017/return-reached.png)。
- [A 场景报告](../environment/REPORT.md)、[B 人物报告](../characters/plato/v001/REPORT.md)。

## 实际证据

| 范围 | 当前结果 | 依据及限制 |
| --- | --- | --- |
| Windows 正式工程 | 构建成功，0 错误／0 警告 | Unity 6000.0.85f1，URP 17.0.4，glTFast 6.20.0；独立产品身份，不需要后端 |
| Player | 37/37 检查通过，0 运行错误 | [新鲜报告](../environment/runs/20261022-214215-017/verification.json)，不是历史测试报告 |
| 构图 | 10 个实体锚点最大偏差 2.428% 画宽 | 实际保存网格顶点／边缘中点、人物 Renderer bounds；原画人工标注约 ±8px，不代表整体还原率 |
| 行走 | 11 个连续端点，通过登阶、绕人、下阶和回望位置 | CharacterController 连续移动；回望眼点偏差 0.02787m；单独墙测的起点瞬移另有披露 |
| 人物交付 | 本地 17/17 检查通过，15 张真实渲染，可编辑 .blend | 28,314 三角形，1.75m，脚底 Y=0，+Z 正前；无骨骼／动画，几何未精修 |
| 独立文件检查 | 21/21 通过 | [清单／哈希／引用／依赖检查](file-contract.json)，正式 Unity 模型副本与 B 导出一致，贴图内嵌，无测试资源运行依赖 |
| 测试隔离 | 原有 1,007 个实质文件哈希全部保持一致 | [重新检查](test-preservation.json)，只覆盖原始快照，缓存和运行日志不在范围内 |
| 短时性能 | 约 59.52 FPS，P95 约 16.67ms | RTX3050／D3D11，约18秒样本；不代表长期或全场性能 |

人物导出 SHA-256：`121d42a2df197fe860410dd7f99317318e368ebd1d5253fb58245d13c6cc33a4`。本轮未提交新 Lux3D 生成或新增费用。

复现：在 production 使用 `scripts/environment/build.ps1` 和 `verify.ps1`；负责人文件检查为 `scripts/verify-integration.py --environment-report qa/environment/runs/20261022-214215-017/verification.json`。测试保全检查为 `scripts/verify-test-preservation.py`。

## 对抗审查产生的实际返工

首轮自动报告通过，但真实图出现悬浮横梁观感、拱墙连接缺失和回望空间过空。负责人否决了视觉结构通过，A 补入连接墙、拱肩、入口和侧廊结构，保持原主相机和参考裁切。

独立审查又发现：锚点只投影参数坐标；连续路线没有到达回望机位。A 最后改为读取真实 Mesh 顶点／实际 Renderer bounds，记录来源对象、网格、索引和坐标；连续行走新增 Z=8 端点及实际眼点截图。独立审查员最终确认两项缺口已修复，没有阻断当前技术 P0 收口的问题。见 [前轮审查快照](adversarial-review-204216.md) 和 [最终复核](adversarial-review-final.md)。

## 程序窗口检查的真实范围

负责人此前用原生窗口实际看到主视图，按2切近景、按4回望、Enter进入漫游，并检查短按 W 的最小响应。该检查没有完成整条物理键鼠漫游路线；记录与日志见 [窗口检查](manual-window-review.json)。

最后一次构建后的窗口复查已启动，但用户按下物理 Escape 停止了电脑操作，未获得最终窗口截图。此后只做文件和报告复核，未恢复界面控制。不能把最终 GPU 离屏截图改称物理窗口截图。

## 保持未通过的范围

- 人物眼嘴、鼻梁、发须、手指和持书关系、披衣尖折／黑缝、原画指天手势。B 保持 `baseline_diagnostic`，没有把转格式或坐标整理称为精修。
- 石材材质、雕塑浮雕、复杂柱头、完整采光结构、完整群像和最终灯光；连接墙仍大面积空白。
- 回望入口之外为未制作的画外区域，侧视可见截断；只接受有限灰盒结构和机位可达性，完整回望美术未通过。
- 远端 Z=27—30 两侧边界尚未完整围合，当前验证路线没有覆盖，不可宣称全场自由漫游安全边界通过。
- 真实 LLM、语音、骨骼、动画、商业权利和完整长期性能未验收。原画照片仅作本地参考，没有打包进 Player。

下一轮应先做单个人物脸手与服饰的真实视觉改善，以及建筑材质／光照小样，通过同条件近景对照后再扩人物数量。当前不安排全人物批量生成。
