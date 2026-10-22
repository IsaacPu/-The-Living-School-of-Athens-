# 正式项目工作边界

- 本目录是正式《雅典学院》项目唯一默认写入范围。遵守上级 `AGENTS.md` 的测试/正式隔离规则。
- 当前 Git 分支为 `art/plato-refinement`，用户于2026-10-23明确授权研究专业角色制作方法并继续精修人物。执行 `qa/characters/plato/v002/BRIEF.md`；先一个可核验局部，不批量生成人物。
- 本工作树根目录等价于原 `production/`。仅在此工作树写入；原production/main、入口工作树、测试项目和v001资产均只读。
- 测试目录可只读参考；需要复用时复制明确文件并记录来源，禁止直接引用或改写测试目录资源。
- 正式项目的运行状态、日志、构建和验收报告均写在本目录下，与测试版独立。
- 不把测试版已经通过的检查、生成记录或截图声明为正式版验证。尚未完成的真实 LLM、动画等能力继续按真实状态披露。
- A 独占 `unity/`、`art/environment/`、`scripts/environment/` 和 `qa/environment/`；B 独占 `art/characters/`、`scripts/characters/` 和 `qa/characters/`。负责人维护共享配置、参考原件、总体文档与 `qa/integration/`。不要改写对方文件。
- 重型 Unity 编译和 Blender 渲染避免同时占满 GPU/内存；先完成脚本与小输出，再协调真实运行。
