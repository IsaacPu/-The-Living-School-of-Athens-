# Einar 阶段 1：五个原始 Mesh 的受限检查

2026-10-23。结论：**原始 Mesh 读取完成，但五个 Mesh 隐式带入完整绑定的一部分。当前停在阶段 1；未生成灰模、独立 `.blend` 或新柏拉图候选。** 原始头部的老年形体尚未通过视觉检查。

## 执行及资源

- 单次运行 `scripts/characters/run-einar-stage1.ps1`；Blender 4.5.15，factory startup、关闭自动执行、后台、4 线程。
- 只赋值 `data_to.meshes`，没有显式请求 Objects、Rig、Collections 或 Scenes。
- 检查本身 3.4963 秒，含启动进程 4.888 秒，退出码 0；OS 峰值工作集 **551.9 MiB**，低于 1.2 GiB；45 秒监控未触发。
- 源文件 91,323,760 字节，前后 SHA256 均为 `1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b`，只读属性保持。未终止其他进程。
- factory scene 对象前后均为 `Camera / Cube / Light`，没有任何来源对象链接到场景。未打开源场景、读取图像像素、执行 Text／driver、求值绑定／修改器／置换、编辑几何、保存 `.blend` 或渲染。

## 原始几何

所有数字及包围盒均来自 Mesh 本地原始数据，不能当作世界变换或姿态结果。

| Mesh | 顶点 | 多边形 | 三角 | UV | Shape Key 条目 | Mesh / Key drivers |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| `DATA_GEO-einar_head` | 4596 | 4522 | 9044 | UVMap, Alignment | 66（含 Basis） | 0 / 63 |
| `DATA_GEO-einar_head.base` | 4596 | 4522 | 9044 | UVMap, Alignment | 0 | 0 / 0 |
| `DATA_GEO-einar_head.base.001` | 4596 | 4522 | 9044 | UVMap, Alignment | 0 | 0 / 0 |
| `DATA_GEO-eye.L` | 802 | 832 | 1600 | Eyes, Iris, UVMap | 6（含 Basis） | 0 / 2 |
| `DATA_GEO-eye.R` | 802 | 832 | 1600 | Eyes, Iris, UVMap | 6（含 Basis） | 0 / 2 |

`.base` 两份包围盒一致：min `[-0.140275851, -0.160853177, 1.404267430]`，max `[0.140277162, 0.084994346, 1.746093631]`。主头仅 Y/Z 最值略有区别；相同计数和相近包围盒不能证明逐顶点相同、完整闭合或视觉合格。

左右眼原始坐标都在原点附近（各轴约 ±0.013），头部 Z 范围为 1.404–1.746。阶段 1 未读取来源眼对象变换，**不能据此确认头眼匹配位置，后续不得猜摆眼球。**

## 隐式依赖

| 新增 ID 类别 | 数量 |
| --- | ---: |
| Objects | 40 |
| Meshes（含所请求的 5 个） | 32 |
| Materials / Images | 14 / 39 |
| Armatures / Actions | 1 / 18 |
| Node Groups / Lattices | 33 / 10 |
| Shape Keys / Libraries | 6 / 1 |
| Texts | 1：`cloudrig.py` |
| Collections / Scenes / Cameras / Lights | 0 / 0 / 0 / 0 |

新增对象含 `RIG-einar`、服装／机械臂对象、晶格与控制形状。其具体引用链未在本次追溯，不能仅凭名称断言是哪一个 Mesh／材质拉入。`cloudrig.py` 只加载了 Text ID，未读取内容或执行。驱动只计数，未读取表达式或求值。

39 个图像 ID 的路径均落在获准缓存并找到对应文件：37 个普通文件、2 个 UDIM ID（分别找到 3／4 个匹配文件），均未打包。此项只证明静态路径存在；未验证图像解码、纹理内容、逐 tile 完整性或渲染兼容。头皮材质引用了 albedo、roughness、dirt、displacement／wrinkle 等图像，完成图中的年龄来源仍不能拆分为已核验几何贡献。

## 当前边界与后续判断

已把数据发给负责人。按负责人关于额外对象／不确定依赖的门槛，当前停在阶段 1，不强开完整场景。

`DATA_GEO-einar_head.base` 没有 Shape Key 或自身 driver，是独立灰模的优先研究对象；但仍引用原材质，**独立提取尚未验证**。若继续，只能把原始顶点／面复制到全新 Mesh，在任何场景求值前移除全部来源 ID 和材质，然后验证剩余数据仅为干净静态头、相机和灯光。无来源对象、绑定、发须、置换、高分贴图或眼球猜摆；保持坐标与拓扑。负责人已给定的一张 640–768px、4 CPU、16–32 samples 三分之四灰模条件仍有效，不能扩大到完整角色。

## 证据和来源

- [完整原始 Mesh／依赖记录](stage1-raw-meshes.json)
- [进程、内存及源保护记录](stage1-run.json)
- `stage1.stdout.log`、`stage1.stderr.log`；后者为空。
- [阶段 0](STAGE0.md)
- [官方来源](https://studio.blender.org/characters/einar/v1/)，[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。保留署名：`Einar Rig (CC-BY) Blender Foundation | studio.blender.org`。本阶段未制作衍生几何；包内额外署名内容尚未读取。
