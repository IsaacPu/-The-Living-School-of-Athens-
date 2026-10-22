# 《雅典学院》正式项目工作区

状态：**P0 中央建筑／一人合模技术样板通过负责人和独立审查。人物精修、完整场景美术与全场漫游尚未通过。**

这里用于接下来的正式场景与人物资产制作。A 场景、B 人物属于同一个正式项目，由项目负责人统一标准并组织集成。

已验收的测试项目独立保存在本机协调工作区的 `test-project/`，不属于这个正式项目仓库。只复制明确需要的文件并记录来源，运行时不得依赖测试目录；旧报告不计入正式验收。

本轮结果、验证范围和未通过项见 [P0 验收记录](qa/integration/P0_ACCEPTANCE.md)。原任务与职责见 [制作任务书](docs/PROJECT_BRIEF.md)。

- [启动 Windows 样板](unity/start-sample.cmd)；需保留 `unity/Builds/P0/` 完整目录。
- [实际主视图](qa/environment/runs/20261022-214215-017/hero.png) · [实际人物近景](qa/environment/runs/20261022-214215-017/close.png) · [连续抵达后的回望](qa/environment/runs/20261022-214215-017/return-reached.png)。
- [A 场景报告](qa/environment/REPORT.md) · [B 人物报告](qa/characters/plato/v001/REPORT.md) · [人物交接清单](art/characters/plato/v001/delivery.json)。

最新 Player 37 项检查通过，人物本地交付 17 项通过；负责人独立检查 21 项通过。测试基线原有 1,007 个实质文件哈希保持一致。上述数字分别证明各自范围，不能累计称为完整产品验收。

正式后端预留端口为 8788；当前建筑与人物样板不需要启动后端或调用 LLM。正式项目的文件、模型、缓存、日志、配置和构建归属本目录。

## 从仓库恢复

本仓库根目录对应本机的 `production/`。源代码、Unity 配置、已生成建筑资产、人物 GLB／Blender 源文件及诊断报告在版本控制内；Unity Library、Builds、日志和便携 Blender 安装包不提交。

在 Unity 6000.0.85f1 中打开 `unity/`，或从仓库根目录执行 `scripts/environment/build.ps1 -UnityEditor <Unity.exe路径>`，重新生成 `unity/Builds/P0/` 后再启动样板。P0 不需要 API Key 或后台服务。

博物馆原画照片和包含照片的叠加对照图仅保留在本地研究目录；来源和校验值见 `references/original/source.json`，代码仓库不包含这些图片。需要重做原画比较时按该来源在本地准备参考文件。测试保全脚本依赖本机协调工作区的原始快照，不能作为全新克隆的默认检查。
