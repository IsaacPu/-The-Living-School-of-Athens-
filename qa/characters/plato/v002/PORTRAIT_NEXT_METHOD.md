# 下一轮头脸与发须方法：仅研究，尚未实施

负责人已确认 p1b 美术否决。保留五官体积和显隐修复的技术证据；不接入 Unity、不增加人物、不处理身体／衣领。本文件只收敛下一次可执行实验，未创建下一版资产、节点图、纹理或渲染。

## 明确参考与许可

主要三维结构参考选 [Fitzwilliam Museum 的 Plato](https://sketchfab.com/3d-models/plato-1df8376b55e347fb9bb4cf49375d6e5a)。已在浏览器核对在线预览和模型页：发布者为博物馆，模型标 CC BY 4.0、约 380.6k 三角；[官方馆藏记录 GR.23.1850](https://data.fitzmuseum.cam.ac.uk/id/object/65492)列出同一模型 ID，注明早期罗马大理石像、原物高 0.355m。其眉额、眼眶、鼻翼和卷发须有可读体积，适合检查“头发／胡须应有立体分束”及柏拉图的雕塑性结构。它仍是石雕，不是写实老人皮肤基底，也不能证明历史真人长相。馆藏照片另标 CC BY-NC-ND，不能把它与 3D 模型的 CC BY 许可混同。

已看 [ryanfb 的 Louvre Pseudo-Seneca 扫描](https://sketchfab.com/3d-models/louvre-pseudo-seneca-photoscan-18ad84ffac884f81bed2aca290b650e2)：模型标 CC BY 4.0、约 100.3k 三角，脸部有明显老年凹凸与下垂；外围却有破碎片和覆盖缺失，**不选为可直接生产的基底**。本轮尚未核验到可直接替换、许可清楚且完整的写实老人基底，不以搜索标题或面数宣称找到成品。两种扫描均未保存资产文件、导入或制作衍生物。

采用两篇作者本人拆解的方法：Carlos Soares 的 [Old Man](https://gamesartist.co.uk/old-man/)先比较同龄、同一人的多角度形体，再进入细节；Artem Erikenov 的 [Man with a Beard](https://80.lv/articles/breakdown-creating-a-man-with-amazing-grooming)按生长方向分区梳引导束，用细发际毛过渡，并独立控制主体毛和灰白毛。教程工程、照片和商业纹理没有因公开文章而获得复用许可。只借鉴工序，不引入其商业软件、纹理或工期承诺。

原画继续决定老人气质、灰白发须和轮廓方向；雕像支持体积，老年案例支持骨肉和毛发生长，不将任一现代人物完整复制成柏拉图。完整核验及许可边界记录在 `art/characters/plato/v002/source/portrait-next-references.json`。

## 可执行路线与停止点

1. **先把年龄做进骨肉大形。** 继续用已有合法基础网格，先去掉 p1b 发壳和须帘，按眼眶／颧骨／鼻底／口角／颏部地标比较正面、侧面、侧前方轮廓。通过区域化雕刻调整眉眼组织下垂、颧下消瘦、口周组织和下颌松弛，保留眼睑包裹眼球、鼻翼和口裂。先审这些体积，再谈浅皱纹和毛孔；不把高斯参数变化或白发颜色当作年龄通过。保留可回退的形体层与原始网格。**若无发灰模仍偏年轻，停在头脸，不能靠胡须遮盖。**
2. **固定发根表面。** 形体确定后生成独立的最终求值表面及有效 UV，供 Hair Curves 的 Surface／Surface UV Map 绑定。遮罩单独标出额顶、鬓角、髭须、左右颊、下颌和颏底，嘴唇、口裂、眼周不长毛；变换一致。头脸后续一旦改变，重新检查发根。现有 Blender 4.5 工具够用，但本项目尚未验证节点装配和交互梳理质量。
3. **只做一个鬓角—脸颊—下颌过渡试片。** 在一侧先梳少量有明确流向的引导束：短鬓角沿皮肤切线下降，颊须先离开皮肤再转向下颌，长须保留前后厚度与左右起伏。长度从颊部向颏底渐变，须尖不在同一高度，不再做整圈等距直帘或不透明头盔壳。髭须左右分开且保留口裂，等该过渡成立后才处理全头。**试片轮廓或根部失败时，禁止用加密曲线救场。**
4. **引导形状成立，再生成细毛。** 用 Blender 自带 Hair Nodes 的分区插值及密度遮罩扩展引导束，再做主束／次束聚束；卷曲、长短变化按区控制，末端保留少量分离毛。头发与长须的弯曲尺度不同；散毛只打破规则，不能承担主体体积。灰白毛通过分组与单根材质变化表现，先在中性材质下检查是否仍像塑料片／幕帘。
5. **逐关视觉验收。** 下一次若获制作与资源窗口，先审无发老年头形，再审一侧过渡，最后才是完整头部。每关检查正／侧／侧前方，但具体输出数量与 CPU 时段由负责人另定，本轮不渲染。通过应看：无毛也可信的老人形体、自然发根、清楚口裂、具有前后层次的胡须、无硬壳边界。不得以曲线数、细分数或技术全绿替代判断。

这条路线需要逐区可视雕刻／梳理及美术判断；现有程序化批量操作尚未证明能自动完成该质量。B 可以负责地标测量、独立源保存、分区／节点组织、许可和技术验证；不能承诺换成 Hair Nodes 就得到可信肖像。若持续缺少形体控制能力，应由负责人决定改走已经完成本地质量核验的老人基底或人工雕刻制作，而非继续加噪声。

资源和软件维持现状：Blender 4.5.15、现有 Python，不安装、付费或调用生成 API。石雕纹理不投为人皮，商业教程纹理不借用。人物运行导出、烘焙、动画和 Unity 均留在后续单独验收，不属于本轮方法研究。

已读的具体操作文档：[Curves Sculpt](https://docs.blender.org/manual/en/4.5/sculpt_paint/curves_sculpting/introduction.html)、[Interpolate](https://docs.blender.org/manual/en/4.5/modeling/geometry_nodes/hair/generation/interpolate_hair_curves.html)、[Clump](https://docs.blender.org/manual/en/4.5/modeling/geometry_nodes/hair/guides/clump_hair_curves.html)、[Curl](https://docs.blender.org/manual/en/4.5/modeling/geometry_nodes/hair/guides/curl_hair_curves.html)。已只读确认现有便携 Blender 包内 `4.5/datafiles/assets/geometry_nodes/procedural_hair_node_assets.blend` 存在，2,465,506 字节；这只证明工具文件存在，不是本项目节点效果已验证。
