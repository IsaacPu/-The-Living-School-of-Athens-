# A-P1 入口技术灰盒验收

分支 `feature/entrance-experience`，仅写本工作树。运行入口为 `unity/start-entrance.cmd`，Player 为 `unity/Builds/Entrance/AthensEntrance.exe`；构建产物和日志不纳入 Git。

| 记录 | 技术结果 | 视觉结论 |
| --- | --- | --- |
| `runs/20261023-032347-097/report.json` | 190/190；9 次进入、9 次返回、3 次取消 | 负责人否决：混合阶段相机不在匹配机位，两套尺度明显错位。原图和报告保留。 |
| `runs/20261023-142048-542/report.json` | 56/56 单轮预览；150 个半透明采样帧固定在 P0 主机位 | 负责人确认原尺度错误修复，允许进入最终技术 QA；仍为 `art_not_accepted`、`not_seamless`。 |
| `runs/20261023-161151-747/report.json` | 197/197；9 次进入、9 次返回、3 次取消；运行时错误 0 | 技术灰盒通过；`art_not_accepted`、`not_seamless` 保留。 |
| `p0-regression/runs/20261023-033126-701/verification.json` | 原保存 P0 场景，新构建 37/37 共享运行时回归 | 仍为原 P0 一人结构样板，不是完整美术。 |

新预览关键帧位于 `runs/20261023-142048-542/`：`gallery-initial.png`、`entry-alignment.png`、`entry-bridge.png`、`entry-match.png`、`entry-middle.png`、`entry-crossed.png`、`academy-after-entry.png`、`gallery-returned.png`。具体人工结论保存在 `visual-review.json`。

最终相同构建的关键帧和轨迹位于 `runs/20261023-161151-747/`。9 次交接的位置、旋转、FOV、投影矩阵最大误差均为 0；1299 个半透明桥接采样帧固定在主机位，最大位置偏差 `1.788139e-7 m`，旋转/FOV/投影偏移误差为 0。独立 Windows 构建 0 错误、0 警告，Unity 6000.0.85f1。

完整验收使用真实 7 秒进入和 6 秒返回，三轮包含正常、跳过、取消后再入、返回后再入；取消分别覆盖 24%、42%、62% 的对准、桥接和混合阶段。自动帧控制器禁用；交接检查最后自动姿态与首个无输入重力帧，阈值为位置 1mm、旋转 0.1°、FOV 0.05°、投影矩阵最大元素差 1e-4。接管后真实移动一步，检查速度×时间、实际地面支撑及内胶囊无穿透。

技术报告是 API 请求驱动的 Player 验证，截图来自同一个实际相机的 URP GPU 渲染。验证期间 `ProductionSample.Update` 跳过用户输入，直接调用 Request/Drive；不证明实体 E/Space/Esc/R、鼠标锁、真实 WASD 首帧或物理窗口展示。重力首帧 Drive 不等于实体输入。独立代码审查未发现必修崩溃或状态损坏问题；上述输入边界保留。

不透明桥接期间画面本身短暂停住，底层镜头在遮盖下移动，不称真实门户。已知差距是群像缺失、人物姿态不同、外框/雕塑/建筑细节与色调不同；半透明时仍有重影。本轮只证明可运行入口闭环和控制交接。

公版复制图来源及哈希见 `art/environment/entrance/source/source.json`。博物馆官方照片仅供本地研究，未打包。房间尺寸、装饰和穿画抬升属于设计补全，不是精确测绘或历史通道。P0 场景、历史报告、人物 v001 字节冻结的静态审查记录见 `static-audit.json`。
