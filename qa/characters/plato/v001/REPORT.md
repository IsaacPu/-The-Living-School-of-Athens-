# B-P0 柏拉图诊断基线

交付状态：`baseline_diagnostic`。本地导入、可编辑源文件、坐标整理、实际检查渲染和导出已完成；人物艺术精修未通过，正式 Unity 集成由 A 另行验证。本报告没有沿用测试版的验收结果。

## 资产与实际变更

- 独立只读源：`production/art/characters/plato/v001/source/plato-lux3d-task-4277623.glb`，Lux3D 国际站任务 `4277623`；SHA-256 `904ab6adec70c941a877918435b3c655a89a6d67be5c52610d4d210689afd8ce`。
- 交接清单：`production/art/characters/plato/v001/delivery.json`。清单中的路径均相对清单自身。
- 实际导出：7,722,596 字节；SHA-256 `121d42a2df197fe860410dd7f99317318e368ebd1d5253fb58245d13c6cc33a4`。
- 脚底到头顶为 1.75m；脚底 Y=0；+Y 向上、+Z 正前。正背面实际渲染已目视确认，整体包围盒顶部为头顶，没有举手超过头顶的情况。这是文件内体尺，不是历史人物真实身高结论。
- 仅把源物体平移至脚底根节点；glTF 平移为 `(0, 0.875, 0)`，尺度仍为 1，没有增加固定 180°旋转。
- 28,314 个三角形形状保留。独立检查逐三角形比较坐标，容差为 0.1mm。Blender 重导出可能因 UV/法线接缝拆点改变顶点数；不能把拆点变化误称为重拓扑。
- 没有平滑、细分、修型、重拓扑、骨骼、动画或新增生成。一个静态网格仍是一个静态网格；可编辑 `.blend` 不代表可换装或已经具备合格绑定母版。

## 实际图片及缺陷定位

原始 PNG 均为 Blender 4.5.15 LTS 本地 CPU/Cycles 渲染，12 samples、去噪开启；不是概念图。采样仅用于诊断，不作为最终美术出图质量。

| 检查 | 实际图片 | 结果与局部定位 |
| --- | --- | --- |
| 正面 | [正面](axis_plus_z_candidate_front.png) | +Z 为正面；双手抱书，与原画的向上指点手势不同（D03） |
| 左侧 | [主体左侧](axis_plus_x_subject_left.png) | 可检查鼻、发须、手臂和披衣厚度；未作侧面解剖修复 |
| 右侧 | [主体右侧](axis_minus_x_subject_right.png) | 保留另一侧检查证据，不能从单侧推断完整性 |
| 背面 | [背面](axis_minus_z_candidate_back.png) | 披衣中段有尖锐三角折面、凹槽与黑缝外观（D05） |
| 脸 | [脸正面](face_front.png)、[脸四分之三](face_three_quarter.png) | 鼻梁、额头和发须棱面明显，眼嘴贴图模糊，眼睑体积不足（D01） |
| 手与书 | [正面局部](hands_book_front.png)、[侧面局部](hands_book_side.png) | 指节不清、手书接触处有狭缝/尖角，封面边缘薄片感明显（D02） |
| 衣褶 | [上身局部](hands_book_front.png) | 紫色上臂和书旁存在黑缝外观；披衣有大块尖折（D04）。黑缝的局部拓扑成因尚未逐处确认，不能全部称为破洞 |
| 足部 | [脚与袍摆](feet_front.png) | 已技术落地；脚趾贴图、脚跟轮廓及袍摆下内部仍粗糙（D06） |
| 标尺 | [脚底与米制标尺](front_metric_ruler.png) | 0—1.75m 的 QA 标尺；标尺、地面、灯光与相机不进入 GLB |

图定位的归一化矩形坐标、缺陷编号及下一轮修复方向见 [visual-review.json](visual-review.json)，同样写入交接清单的 `known_defects`。

补充拓扑诊断（D09）：以 1 微米位置量化合并后，统计为 0 条边界边、579 条由超过两个三角形共享的边。接触或重合面也可能影响该统计，尚未逐处定位。因此黑缝只记录为视觉异常，不擅自断言全部为破洞，也不执行自动焊接/修复。

## 材质与同条件比较

- 交付 GLB 保留原件材质：一个不透明材质，底色和金属度/粗糙度各一张 2048×2048 贴图，两张均内嵌，无外部贴图依赖，无 normal map。
- [原材质](material_before.png)与[金属度归零候选](material_nonmetal_candidate.png)采用完全相同的相机、灯光、采样和画幅。候选并未解决脸手和尖折；没有充分依据对整个人物一刀切覆盖金属度，因此交付仍保留原材质。实验只保存在工作文件和 QA 图片中（D07）。
- [源文件整理前](source_before_same_conditions.png)与[交付整理后](delivery_after_same_conditions.png)采用同一套相对机位、灯光和地面。整理前从只读原件重新导入，舞台整体随源模型下移 0.875m，保持相同相对条件；该补偿记录于 [roundtrip.json](roundtrip.json)。两图用于证明坐标整理没有制造外观改善，不宣称精修。
- 导出器有一条多图像节点对应纹理采样器的警告，已保留在 [blender.log](blender.log)。实际 GLB 的两张贴图内嵌和重新导入已检查；正式 Unity 的材质表现仍需 A 验证。

## 验证、回退与后续边界

实际 `.blend` 已重新打开，导出 GLB 已在空场景重新导入；结果见 [roundtrip.json](roundtrip.json)。字节级核查和交接清单引用检查见 [verification.json](verification.json)。

复现从 `production/` 运行：

```powershell
.\scripts\characters\run-plato-diagnostic.ps1 -BlenderExe <负责人核验的便携 Blender 路径>
```

入口依次运行实际渲染/导出、`roundtrip-ruler.py` 的标尺与重新导入、`package-plato.py` 的清单打包，以及 `verify-plato.mjs` 的最终验证。精确首次执行参数记录于 [execution.json](execution.json)，补充执行输出见 [roundtrip.log](roundtrip.log)。仅收口核查时可单独运行打包器与 verifier，无需再次渲染。

回退使用只读 source 文件；坐标平移逆变换为 glTF `(0, -0.875, 0)`。原材质没有在交付 GLB 中修改，无需材质回退。

下一轮局部重建建议：先统一原画角色设定，重建头脸与眼睑，再建立中性手部/书籍的可编辑结构，最后处理指天手势和披衣受力。该建议没有在本轮实施。商业权利、最终原画辨识度、正式 Unity 导入、运行成本、动画和可换装均未验收。本轮没有付费服务调用、采购或外包。
