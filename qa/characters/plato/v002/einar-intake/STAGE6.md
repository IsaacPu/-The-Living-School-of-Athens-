# 静态眼睛与皮肤：下一张近景方案

2026-10-23。**已有来源数据足以准备无 rig 的静态眼球候选和简化皮肤基础层；尚未制作新近景或验证最终适配。** 目标是一张可审查的专业基底成像原型，不是源 rig 中性姿态复刻或柏拉图完成。负责人已认可阶段 5 原参数恢复及可见改善，老年柏拉图门槛仍未通过。

后续：负责人已选择简化三分区眼表面并放行唯一近景，实际结果见 [阶段7](STAGE7.md)；本页保留静态依据与当时方案，不表示还在等待该次许可。

## 眼睛依据与假设

- 每眼 802 顶点／832 面，材质分区明确：pupil 128、iris 192、white 512；UV 为 Eyes／Iris／UVMap。两眼的 world/local API 矩阵在未链接、未求值读取状态均为 identity，不能当作有效世界姿态。
- 主头使用 `GEO-einar_head` 参照，Basis 平移 `(0,-.000167568,.054400042)`；主头／两眼同 parent `RIG-einar`，parent_inverse 均 identity。按 `M_head_basis^-1 * M_eye_basis` 得来源通道候选中心：L `(.028967,-.110039,1.622061)`，R `(-.029815,-.112316,1.622656)`，旋转／scale 也保留矩阵记录。未使用 helper.base 的对象偏移，也不凭感觉调整。
- 两眼启用 Armature constraint／modifier。上述候选明确忽略它们，因此仅是来源保存通道的静态重建，需要干净几何与实际近景确认眼睑接合，不能称已求值 neutral。
- Key 的 active Action=None、NLA=[]；drivers 仅 Shrink／Grow。`resize`、`GEO-resize2_pupil`、`GEO-resize2_iris` 均未驱动、未 mute、relative=Basis、值为 1；可按 `Basis + Σ(key-relative)*1` 独立恢复这三层。Mesh.vertices 与 Basis 相同，不能直接省略这些层；驱动 Shrink／Grow 明确不加入。
- 首版元数据中的 eligibility 曾因用 Python `is` 比较 RNA wrapper 误报 false；已根据同次记录的唯一 Basis 名／driver／Action／NLA 证据修正，脚本改用 pointer 相等，没有为此重复载库。新眼球资产尚未创建，完整坐标数组将在获准原型阶段提取。

## 可独立用的皮肤资源

`einar_skin.albedo` 为 sRGB、UVMap，4096² RGB8；`einar_skin.roughness` 为 Non-Color、UVMap，1024² 单通道8bit。两图可直接用于新基础 PBR 材质；原 Base Color 还经过多级 Mix，原 Roughness 经 remap，故该版本须标为**简化基础层**，不能称完整源 neutral shader。

EF packed 图的 Blue 是默认层候选，Alpha 经减 .5、乘 2 进入细节 Bump；其总合成／权重涉及 Attribute，而旧 JSON 未保存 attribute_name。已有真实默认几何时再叠 Blue 还可能重复。第一张先不加载 packed 图，不新增皱纹、不把 linked 缓存值当 neutral。眼睛 `eyes.albedo` 已仅读头确认 2048² RGB8／sRGB，但 SH-eye_ball 的 atlas UV／iris_depth 分支未展开，不能猜用哪层 UV 或声称完整眼 shader。

## 一张近景的具体执行方案（待负责人放行）

1. 从阶段 5 独立 `.blend` 重开，顺带核验 `//textures/disp_default.exr` 可解析及 SHA；保留原 Catmull-Clark 2／默认九节点雕刻、原 Midlevel／Scale，不重新调年龄参数。
2. 新建无 driver／约束的眼 Mesh，按三层静态 Key 公式和上述 Basis 相对矩阵建立来源通道候选，保留面分区／UV／source render Subsurf2。先做几何接合检查；不以偏移“修好看”。实际适配由唯一近景复核。
3. 皮肤仅用来源 albedo／roughness 基础图，保留明确未链接的来源 IOR 1.45；其余简化材质参数应明确记录为原型设置，不冒充完整皮肤。眼表面优先补齐已有 SH-eye_ball 的 atlas UV 静态依据后才用 atlas；若不补，须明确选择只保留源三分区的简化眼材质，不能宣称完整眼成像恢复。这个差异在放行单图时需明确。
4. 单张 768² 三分之四头部近景、Cycles CPU 4／16 samples；沿用阶段 5 不过曝灯光 8／2／6W 与 exposure 0，画幅只收紧到头部。无发须／身体／源场景／rig／表情图。纹理复制到新衍生目录、记录 SHA／CC BY／改动，用相对路径；不以 root 缓存作最终依赖。
5. 只出一次图即停。看眼球是否悬空／穿眼睑、五官可读性、皮肤与雕刻的实际贡献；不把该简化原型不足扩大为完整 Einar 失败，也不称柏拉图完成。

| 新增基础图 | 原生缓冲 | 同源通道 float32 | 如扩为 RGBA float32 |
| --- | ---: | ---: | ---: |
| albedo 4k RGB8 | 48 MiB | 192 MiB | 256 MiB |
| roughness 1k 灰8 | 1 MiB | 4 MiB | 16 MiB |
| eyes.albedo 2k RGB8（映射确认后） | 12 MiB | 48 MiB | 64 MiB |

默认 EXR 已包含在阶段 5 实测约 650 MiB 峰值内。加上述三图的单份 RGBA float32 336 MiB，粗基数约 **986 MiB**；未包含副本／mipmap／新增 shader 开销，不能当容量通过。若先不用眼 atlas，则约 922 MiB。packed EF 额外 256 MiB 当前不加载。保持 **45s／1.2 GiB 自己 PID 硬限**，超限退出保留日志，不偷偷降精度或换源。

必要证据：`stage6-eye-metadata.json`、`stage6-head-transform-reference.json`、`stage6-eye-static-keys.json`、`stage6-skin-static-plan.json`、`stage6-eye-albedo-header.json` 与三次 run／日志。眼 Object、主头参照、静态 Key 检查分别 4.863s／536.14 MiB、4.873s／551.67 MiB、4.928s／537.19 MiB，均 exit0，源哈希／只读保持。皮肤与眼 atlas 仅额外读取 558 字节文件头，无像素解码／新渲染。
