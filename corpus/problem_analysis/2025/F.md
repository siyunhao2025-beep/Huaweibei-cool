# 2025 年 F 题：影像分割与纹理/形态分析

> 证据等级：**C（商业资料，仅供参考）**。来源：`2025华为杯F题初步解题思路-L老师.pdf`（15 万字符，代码完整）。

## 一、题面主题与任务拆解

本题为**RGB 图像的多目标分割、纹理与形态分析**。L 老师思路代码用 skimage 做 KMeans 分割 + LBP 纹理 + Canny 边缘 + 骨架化 + 距离变换 + 香农熵。

- **第 1 问**：RGB → LAB 颜色空间 + LBP 纹理 + Canny 边缘特征 → **KMeans 聚类分割**（K=5）。
- **第 2 问**：目标轮廓提取与形态学处理（binary opening/closing、disk 结构元、remove_small_objects）。
- **第 3 问**：骨架化（skeletonize）+ 概率 Hough 直线（probabilistic_hough_line）+ 距离变换（EDT）。
- **第 4 问**：香农熵（shannon_entropy）纹理/复杂度度量。

## 二、数据模态与规模

- RGB 图像（demo 生成椭圆/圆/矩形/正弦路径合成图；真实数据为医学/遥感影像）。
- 规模：单图 ~1100px 边长。

## 三、官方硬约束

- 待确认（图像分辨率/类别数）。

## 四、题型原型判断

**图像处理 + 无监督分割 + 形态学/纹理**。依据：KMeans、LBP、Canny、Hough、骨架、EDT、熵。

## 五、方法谱系

| 方法 | 频次 | 出处 |
|---|---|---|
| KMeans 聚类分割（LAB+LBP+边缘） | 高 | F 题初步思路 |
| LBP 局部二值模式纹理 | 高 | F 题初步思路 |
| Canny 边缘 / 形态学 disk | 高 | F 题初步思路 |
| 骨架化 skeletonize | 中 | F 题初步思路 |
| 概率 Hough 直线 | 中 | F 题初步思路 |
| 距离变换 EDT / 香农熵 | 中 | F 题初步思路 |

## 六、推荐/备选路线

- 主流：LAB+LBP+Canny 特征 → KMeans 分割 → 形态学清理 → 骨架/Hough/EDT/熵分析。
- 创新：U-Net/语义分割替代 KMeans；超像素 SLIC；深度学习纹理分类。

## 七、避坑点

- KMeans 对颜色敏感，先转 LAB 再聚类。
- 边缘要膨胀成特征通道（避免细碎边缘噪声）。
- 类别数 K 需通过轮廓/误差曲线选。

## 八、代码盘点

- F 题思路 PDF 内嵌完整 Python 代码（PIL/skimage/scipy.ndimage/sklearn.cluster.KMeans）。
- 无散 .py 文件（代码在 PDF 内）。

## 九、成品论文

- 渠道二 F 题仅 5 文件（1 思路 PDF + 资料），无独立成品论文。

## 十、来源文件

- `25华为杯...\渠道二\0-2025 F题...\L老师\2025华为杯F题初步解题思路-L老师.pdf`
