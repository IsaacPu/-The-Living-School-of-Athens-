# Einar 阶段 0：库目录读取完成

按负责人授权，仅执行一次 Blender 4.5.15 后台目录读取：`--background --factory-startup --disable-autoexec --threads 4`，通过 `bpy.data.libraries.load` 只读 `data_from` 名称列表，没有给任何 `data_to` 属性赋值。未打开原场景、追加源数据、求值对象／修改器／驱动、执行 Text、读取图像像素或渲染。独立检查员先做了脚本静态审查。

目录读取 2.1042 秒；含 Blender 启动的进程总耗时 3.749 秒。进程峰值工作集 439.94MiB，读完时工作集 169.54MiB，已正常退出。这是目录读取的资源消耗，不能用于推断提取头部或完整场景的内存。

| 数据类别 | 名称数量 |
| --- | ---: |
| Objects | 392 |
| Meshes | 262 |
| Materials | 95 |
| Images | 64 |
| Collections | 49 |
| Armatures | 5 |
| Actions | 34 |
| Node groups | 86 |
| Texts | 4 |
| Curves | 46 |
| Lattices | 18 |
| Cameras / Lights / Scenes | 2 / 16 / 1 |

头部候选对象名称包括 `GEO-einar_head`、`GEO-einar_head.base`、`GEO-einar_head.base.001`；目录也存在对应 `DATA_...` 网格名称。左右眼 `GEO-eye.L/R` 与对应网格，以及 cornea／meniscus／plica／eye_anim 名称均可见。**只是名称命中，不能据此判断实际几何、依赖或哪个版本适合提取。** 本阶段不暴露独立 `shape_keys` 目录，未检查形状键或激活值。

4 个 Text 名称为 `ReadMe.txt`、`cloudrig.py`、`einar_post_gen.py`、`satchel_post_gen.py`，未加载其内容或执行。5 个 Armature 名称也只见于目录，不代表 rig 可用。64 个图像名称不等于已检查 64 个文件或其路径／像素，依赖完整性仍待审。

读取前后各类驻留数据块数量完全一致：仍为工厂场景的 3 个对象、1 个网格、2 个材质、2 个图像、1 个集合，Armature／Action／Text 等仍为零。独立 PowerShell 检查确认源文件读取前后保持 91,323,760 字节、ReadOnly，SHA256 均为 `1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b`。没有修改缓存。

完整名称列表及进程内存见 `stage0-metadata.json`；进程耗时和源保护见 `stage0-run.json`；原始输出见 `stage0.log`。脚本为 `scripts/characters/inspect-einar-catalogue.py`。缓存绝对路径仅用于来源核验，没有写入 Unity 或候选资产依赖。

停止点：等负责人决定下一阶段是否能仅加载特定头／眼数据；目前尚未检查实际网格、父级、坐标、形状键、修改器、材料依赖或老年大形。MakeHuman 仅按负责人信息保留为后备，未并行获取或制作。后续 intake 状态集中记录，不为每条协调消息分别提交。
