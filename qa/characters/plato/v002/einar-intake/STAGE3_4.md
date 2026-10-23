# Einar：原始几何、材质与真实雕刻载体

2026-10-23。**已找到来源默认雕刻的真实几何链：基础头的 Subsurf → `SH-Base Displacement` Geometry Nodes。上一张 raw 灰模移除了它，不能据此评价完整 Einar 的老人形体。** 本轮仅静态读取，无几何制作、像素解码、修改器／绑定求值或新渲染。

## 实际数据

- 主头 Mesh.vertices 与其 Basis 逐点完全相同；两份 `.base` 逐点完全相同。主头／Basis 与 `.base` 最大差 `0.002772760923`、RMS `0.000530636173` 源坐标单位，2363 个顶点不同，三个 Mesh 面索引顺序一致。若按米制换算，最大差约 2.773mm；未加载来源 Scene，不能把单位和世界变换当作已核验。
- 66 个 Key 的相对 Key 名和缓存值均已记录，16 个非零；两个 `JawOpen+LipsWide.*.001` 为 1。未执行 63 条 Key drivers，缓存值不等于已求值中性姿态。
- 材质 `einar.skin` 虽标记 `BOTH`，active Material Output.Displacement 未连接；9 个递归材质树中无 Displacement／VectorDisplacement 节点。`disp_default` 在材质中走标量表面参数支路；packed `shapes-*` 分通道走 Bump。**这只描述材质，不能推出对象没有几何位移。**
- `GEO-einar_head` 实际 8 个修改器：Armature → CorrectiveSmooth → Subsurf → 左右眼部 Lattice → `Displacement_Face` → Store Attributes → Stretch Map。没有 Multires 或传统 DISPLACE。主头的 Geometry Nodes 默认图／表情图参与几何，不能只看材质图。
- 两份 `.base` 各 3 个修改器：Subsurf → **`SH-Base Displacement` (`texture_displacement`)** → Store Face Area。Subsurf 为 Catmull-Clark，`render_levels=2`、quality 3、UV `PRESERVE_BOUNDARIES`、boundary `ALL`、use_limit_surface=true；viewport 缓存 levels 分别 0／2，受 driver 控制，不能称中性求值结果。
- 默认位移修改器开启 viewport／render，实际参数是 `Image=disp_default`，Vector 使用命名属性 `UVMap`，**Midlevel=0.5，Scale=0.00800000038**。该 Scale 来自几何修改器，未借用 Bump Distance。
- `texture_displacement` 仅 9 节点，无 driver：Image Texture（Linear／REPEAT）→ 标量减 Midlevel → 乘 Scale → Normal 向量缩放 → CORNER 域 Capture Attribute → Set Position.Offset。即 `offset = normal × (sample(disp_default, UVMap) - 0.5) × 0.00800000038`。这是沿几何法线的标量位移，不是 RGB 矢量置换。主头 `Displacement_Face` 为 118 节点，包含默认和 6 张表情图；不必为默认静态头运行整套表情／绑定。
- `ReadMe.txt` 仅按文本读取，确认 CC BY 4.0；其中启用附加组件／重载执行脚本的建议未执行。官方制作流程由负责人核验并提供为线索：[workflow](https://studio.blender.org/training/realistic-human-research/workflow/)。上述修改器和公式则由本机源文件静态数据直接证实。

## 图像头与资源预算

独立检查员仅读 853 字节文件头，结果与负责人另存的三张图头记录吻合；未读取像素。

| 图像 | 尺寸／通道 | 原样本类型 | 原生单缓冲 | 同通道 float32 |
| --- | --- | --- | ---: | ---: |
| `disp_default.exr` | 4096²，单 Y | HALF，ZIP | 32 MiB | 64 MiB |
| `shapes-A-B-C-D.tif` | 4096²，RGBA | uint16，Deflate | 128 MiB | 256 MiB |
| `shapes-E-F-DEFAULT-DETAIL.tif` | 4096²，RGBA | uint16，Deflate | 128 MiB | 256 MiB |
| `noise_04.tif` | 1024²，RGB | uint16，Deflate | 6 MiB | 12 MiB |

四张合计 588 MiB 只是单份 float32 通道缓冲，不含扩展／副本／mipmap／渲染。最小默认雕刻仅需 `disp_default`，不要同载整套图。Blender 若将单 Y 扩成 float32 RGBA，则一份为 **256 MiB**；真实解码与峰值尚未测。已有纯灰渲染峰值约 505 MiB，加这一份为约 761 MiB 的粗略单缓冲基数，仍需给细分和副本留空间，不能当容量通过。

原网格经 JSON 实查全部 4522 个四边面。标准 Catmull-Clark 的拓扑预算：L2 约 72666 顶点／72352 四边面，L3 约 290042／289408；这是拓扑推算，未实际求值。优先匹配源文件 render L2，后续如需 L3 必须另记录保真与资源取舍。任何后续运行仍需 4 CPU／1.2 GiB／45 秒、只监控自己的 PID。

## 下一最小恢复依据与剩余边界

可准备独立 raw `.base`，保留实际 `UVMap` 角点数据和来源存在的 crease 等细分属性，按源 Catmull-Clark 参数及这 9 个节点重建默认层，只读取单张默认 EXR；无来源对象、rig、表情图、毛发、原材质或眼球猜摆。UV 数据／细分属性的具体复制及图像解码、干净默认层求值和新灰模均**尚未执行**，当前不是恢复成功或艺术通过。

进程证据：阶段 3 成功 5.096s／548.61 MiB；阶段 4 对象读取 5.370s／553.21 MiB；随后仅节点组读取 3.758s／440.95 MiB，均退出 0。阶段 3 首试汇总时因 library API 替换传入名单发生键错误，失败记录保留，修正复制名单后完成原范围。所有运行前后源 `.blend` 大小／SHA256／只读保持，来源对象未链接场景，无其他进程被终止。

必要证据：`stage3-displacement-static.json`、`stage3-chain-summary.json`、`stage3-image-headers.json`、`stage4-head-modifiers-static.json`、`stage4-geometry-nodes-static.json` 以及对应 run JSON／stdout／stderr。来源／署名保持 **Einar Rig (CC-BY) Blender Foundation | studio.blender.org**，[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。
