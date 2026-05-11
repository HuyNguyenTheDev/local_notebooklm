import io
import sys

from backend.config import CHUNK_OVERLAP, CHUNK_SIZE
from backend.services.chunker import split_text


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def _shared_overlap_len(left: str, right: str, max_chars: int = 300) -> int:
    max_len = min(max_chars, len(left), len(right))
    for size in range(max_len, 0, -1):
        if left[-size:] == right[:size]:
            return size
    return 0


def main() -> None:
    raw_text = (
        """
EfﬁcientNet: Rethinking Model Scaling for Convolutional Neural Networks
Mingxing Tan1 Quoc V . Le1
Abstract
Convolutional Neural Networks (ConvNets) are
commonly developed at a ﬁxed resource budget,
and then scaled up for better accuracy if more
resources are available. In this paper, we sys-
tematically study model scaling and identify that
carefully balancing network depth, width, and res-
olution can lead to better performance. Based
on this observation, we propose a new scaling
method that uniformly scales all dimensions of
depth/width/resolution using a simple yet highly
effective compound coefﬁcient. We demonstrate
the effectiveness of this method on scaling up
MobileNets and ResNet.
To go even further, we use neural architec-
ture search to design a new baseline network
and scale it up to obtain a family of models,
called EfﬁcientNets, which achieve much
better accuracy and efﬁciency than previous
ConvNets. In particular, our EfﬁcientNet-B7
achieves state-of-the-art 84.3% top-1 accuracy
on ImageNet, while being 8.4x smaller and
6.1x faster on inference than the best existing
ConvNet. Our EfﬁcientNets also transfer well and
achieve state-of-the-art accuracy on CIFAR-100
(91.7%), Flowers (98.8%), and 3 other transfer
learning datasets, with an order of magnitude
fewer parameters. Source code is at https:
//github.com/tensorflow/tpu/tree/
master/models/official/efficientnet.
1. Introduction
Scaling up ConvNets is widely used to achieve better accu-
racy. For example, ResNet (He et al., 2016) can be scaled
up from ResNet-18 to ResNet-200 by using more layers;
Recently, GPipe (Huang et al., 2018) achieved 84.3% Ima-
geNet top-1 accuracy by scaling up a baseline model four
1Google Research, Brain Team, Mountain View, CA. Corre-
spondence to: Mingxing Tan <tanmingxing@google.com>.
Proceedings of the 36 th International Conference on Machine
Learning, Long Beach, California, PMLR 97, 2019.
0 20 40 60 80 100 120 140 160 180
Number of Parameters (Millions)
74
76
78
80
82
84Imagenet Top-1 Accuracy (%)
ResNet-34
ResNet-50
ResNet-152
DenseNet-201
Inception-v2
Inception-ResNet-v2
NASNet-A
NASNet-A
ResNeXt-101
Xception
AmoebaNet-A
AmoebaNet-C
SENet
B0
B3
B4
B5
B6
EfﬁcientNet-B7
Top1 Acc. #ParamsResNet-152 (He et al., 2016)77.8% 60MEfﬁcientNet-B1 79.1% 7.8MResNeXt-101 (Xie et al., 2017)80.9% 84MEfﬁcientNet-B3 81.6% 12MSENet (Hu et al., 2018)82.7% 146MNASNet-A (Zoph et al., 2018)82.7% 89MEfﬁcientNet-B4 82.9% 19MGPipe (Huang et al., 2018)† 84.3% 556MEfﬁcientNet-B7 84.3% 66M†Not plotted
Figure 1.Model Size vs. ImageNet Accuracy. All numbers are
for single-crop, single-model. Our EfﬁcientNets signiﬁcantly out-
perform other ConvNets. In particular, EfﬁcientNet-B7 achieves
new state-of-the-art 84.3% top-1 accuracy but being 8.4x smaller
and 6.1x faster than GPipe. EfﬁcientNet-B1 is 7.6x smaller and
5.7x faster than ResNet-152. Details are in Table 2 and 4.
time larger. However, the process of scaling up ConvNets
has never been well understood and there are currently many
ways to do it. The most common way is to scale up Con-
vNets by their depth (He et al., 2016) or width (Zagoruyko &
Komodakis, 2016). Another less common, but increasingly
popular, method is to scale up models by image resolution
(Huang et al., 2018). In previous work, it is common to scale
only one of the three dimensions – depth, width, and image
size. Though it is possible to scale two or three dimensions
arbitrarily, arbitrary scaling requires tedious manual tuning
and still often yields sub-optimal accuracy and efﬁciency.
In this paper, we want to study and rethink the process
of scaling up ConvNets. In particular, we investigate the
central question: is there a principled method to scale up
ConvNets that can achieve better accuracy and efﬁciency?
Our empirical study shows that it is critical to balance all
dimensions of network width/depth/resolution, and surpris-
ingly such balance can be achieved by simply scaling each
of them with constant ratio. Based on this observation, we
propose a simple yet effective compound scaling method.
Unlike conventional practice that arbitrary scales these fac-
tors, our method uniformly scales network width, depth,
arXiv:1905.11946v5  [cs.LG]  11 Sep 2020
EfﬁcientNet: Rethinking Model Scaling for Convolutional Neural Networks
(a) baseline (b) width scaling (c) depth scaling (d) resolution scaling (e) compound scaling
#channels
layer_i
resolution HxW
wider
deeper
higher 
resolution higher 
resolution
deeper
wider
Figure 2.Model Scaling. (a) is a baseline network example; (b)-(d) are conventional scaling that only increases one dimension of network
width, depth, or resolution. (e) is our proposed compound scaling method that uniformly scales all three dimensions with a ﬁxed ratio.
and resolution with a set of ﬁxed scaling coefﬁcients. For
example, if we want to use 2N times more computational
resources, then we can simply increase the network depth by
αN, width by βN, and image size by γN, where α,β,γ are
constant coefﬁcients determined by a small grid search on
the original small model. Figure 2 illustrates the difference
between our scaling method and conventional methods.
Intuitively, the compound scaling method makes sense be-
cause if the input image is bigger, then the network needs
more layers to increase the receptive ﬁeld and more channels
to capture more ﬁne-grained patterns on the bigger image. In
fact, previous theoretical (Raghu et al., 2017; Lu et al., 2018)
and empirical results (Zagoruyko & Komodakis, 2016) both
show that there exists certain relationship between network
width and depth, but to our best knowledge, we are the
ﬁrst to empirically quantify the relationship among all three
dimensions of network width, depth, and resolution.
We demonstrate that our scaling method work well on exist-
ing MobileNets (Howard et al., 2017; Sandler et al., 2018)
and ResNet (He et al., 2016). Notably, the effectiveness of
model scaling heavily depends on the baseline network; to
go even further, we use neural architecture search (Zoph
& Le, 2017; Tan et al., 2019) to develop a new baseline
network, and scale it up to obtain a family of models, called
EfﬁcientNets. Figure 1 summarizes the ImageNet perfor-
mance, where our EfﬁcientNets signiﬁcantly outperform
other ConvNets. In particular, our EfﬁcientNet-B7 surpasses
the best existing GPipe accuracy (Huang et al., 2018), but
using 8.4x fewer parameters and running 6.1x faster on in-
ference. Compared to the widely used ResNet-50 (He et al.,
2016), our EfﬁcientNet-B4 improves the top-1 accuracy
from 76.3% to 83.0% (+6.7%) with similar FLOPS. Besides
ImageNet, EfﬁcientNets also transfer well and achieve state-
of-the-art accuracy on 5 out of 8 widely used datasets, while
reducing parameters by up to 21x than existing ConvNets.
2. Related Work
ConvNet Accuracy: Since AlexNet (Krizhevsky et al.,
2012) won the 2012 ImageNet competition, ConvNets have
become increasingly more accurate by going bigger: while
the 2014 ImageNet winner GoogleNet (Szegedy et al., 2015)
achieves 74.8% top-1 accuracy with about 6.8M parameters,
the 2017 ImageNet winner SENet (Hu et al., 2018) achieves
82.7% top-1 accuracy with 145M parameters. Recently,
GPipe (Huang et al., 2018) further pushes the state-of-the-art
ImageNet top-1 validation accuracy to 84.3% using 557M
parameters: it is so big that it can only be trained with a
specialized pipeline parallelism library by partitioning the
network and spreading each part to a different accelera-
tor. While these models are mainly designed for ImageNet,
recent studies have shown better ImageNet models also per-
form better across a variety of transfer learning datasets
(Kornblith et al., 2019), and other computer vision tasks
such as object detection (He et al., 2016; Tan et al., 2019).
Although higher accuracy is critical for many applications,
we have already hit the hardware memory limit, and thus
further accuracy gain needs better efﬁciency.
ConvNet Efﬁciency: Deep ConvNets are often over-
parameterized. Model compression (Han et al., 2016; He
et al., 2018; Yang et al., 2018) is a common way to re-
duce model size by trading accuracy for efﬁciency. As mo-
bile phones become ubiquitous, it is also common to hand-
craft efﬁcient mobile-size ConvNets, such as SqueezeNets
(Iandola et al., 2016; Gholami et al., 2018), MobileNets
(Howard et al., 2017; Sandler et al., 2018), and ShufﬂeNets
EfﬁcientNet: Rethinking Model Scaling for Convolutional Neural Networks
(Zhang et al., 2018; Ma et al., 2018). Recently, neural archi-
tecture search becomes increasingly popular in designing
efﬁcient mobile-size ConvNets (Tan et al., 2019; Cai et al.,
2019), and achieves even better efﬁciency than hand-crafted
mobile ConvNets by extensively tuning the network width,
depth, convolution kernel types and sizes. However, it is
unclear how to apply these techniques for larger models that
have much larger design space and much more expensive
tuning cost. In this paper, we aim to study model efﬁciency
for super large ConvNets that surpass state-of-the-art accu-
racy. To achieve this goal, we resort to model scaling.
Model Scaling: There are many ways to scale a Con-
vNet for different resource constraints: ResNet (He et al.,
2016) can be scaled down (e.g., ResNet-18) or up (e.g.,
ResNet-200) by adjusting network depth (#layers), while
WideResNet (Zagoruyko & Komodakis, 2016) and Mo-
bileNets (Howard et al., 2017) can be scaled by network
width (#channels). It is also well-recognized that bigger
input image size will help accuracy with the overhead of
more FLOPS. Although prior studies (Raghu et al., 2017;
Lin & Jegelka, 2018; Sharir & Shashua, 2018; Lu et al.,
2018) have shown that network depth and width are both
important for ConvNets’ expressive power, it still remains
an open question of how to effectively scale a ConvNet to
achieve better efﬁciency and accuracy. Our work systemati-
cally and empirically studies ConvNet scaling for all three
dimensions of network width, depth, and resolutions.
3. Compound Model Scaling
In this section, we will formulate the scaling problem, study
different approaches, and propose our new scaling method.
3.1. Problem Formulation
A ConvNet Layer i can be deﬁned as a function: Yi =
Fi(Xi), where Fi is the operator, Yi is output tensor, Xi is
input tensor, with tensor shape⟨Hi,Wi,Ci⟩1, where Hiand
Wi are spatial dimension and Ci is the channel dimension.
A ConvNet Ncan be represented by a list of composed lay-
ers: N= Fk⊙...⊙F2 ⊙F1(X1) =⨀
j=1...kFj(X1). In
practice, ConvNet layers are often partitioned into multiple
stages and all layers in each stage share the same architec-
ture: for example, ResNet (He et al., 2016) has ﬁve stages,
and all layers in each stage has the same convolutional type
except the ﬁrst layer performs down-sampling. Therefore,
we can deﬁne a ConvNet as:
N=
⨀
i=1...s
FLi
i
(
X⟨Hi,Wi,Ci⟩
)
(1)
where FLi
i denotes layer Fi is repeated Li times in stage i,
⟨Hi,Wi,Ci⟩denotes the shape of input tensor X of layer
1For the sake of simplicity, we omit batch dimension.
i. Figure 2(a) illustrate a representative ConvNet, where
the spatial dimension is gradually shrunk but the channel
dimension is expanded over layers, for example, from initial
input shape ⟨224,224,3⟩to ﬁnal output shape ⟨7,7,512⟩.
Unlike regular ConvNet designs that mostly focus on ﬁnd-
ing the best layer architecture Fi, model scaling tries to ex-
pand the network length (Li), width (Ci), and/or resolution
(Hi,Wi) without changing Fi predeﬁned in the baseline
network. By ﬁxing Fi, model scaling simpliﬁes the design
problem for new resource constraints, but it still remains
a large design space to explore different Li,Ci,Hi,Wi for
each layer. In order to further reduce the design space, we
restrict that all layers must be scaled uniformly with con-
stant ratio. Our target is to maximize the model accuracy
for any given resource constraints, which can be formulated
as an optimization problem:
max
d,w,r
Accuracy
(
N(d,w,r )
)
s.t. N(d,w,r ) =
⨀
i=1...s
ˆFd·ˆLi
i
(
X⟨r·ˆHi,r·ˆWi,w·ˆCi⟩
)
Memory(N) ≤target memory
FLOPS(N) ≤target ﬂops
(2)
where w,d,r are coefﬁcients for scaling network width,
depth, and resolution; ˆFi,ˆLi, ˆHi, ˆWi, ˆCi are predeﬁned pa-
rameters in baseline network (see Table 1 as an example).
3.2. Scaling Dimensions
The main difﬁculty of problem 2 is that the optimal d,w,r
depend on each other and the values change under different
resource constraints. Due to this difﬁculty, conventional
methods mostly scale ConvNets in one of these dimensions:
Depth (ddd): Scaling network depth is the most common way
used by many ConvNets (He et al., 2016; Huang et al., 2017;
Szegedy et al., 2015; 2016). The intuition is that deeper
ConvNet can capture richer and more complex features, and
generalize well on new tasks. However, deeper networks
are also more difﬁcult to train due to the vanishing gradient
problem (Zagoruyko & Komodakis, 2016). Although sev-
eral techniques, such as skip connections (He et al., 2016)
and batch normalization (Ioffe & Szegedy, 2015), alleviate
the training problem, the accuracy gain of very deep network
diminishes: for example, ResNet-1000 has similar accuracy
as ResNet-101 even though it has much more layers. Figure
3 (middle) shows our empirical study on scaling a baseline
model with different depth coefﬁcient d, further suggesting
the diminishing accuracy return for very deep ConvNets.
Width (www): Scaling network width is commonly used for
small size models (Howard et al., 2017; Sandler et al., 2018;
EfﬁcientNet: Rethinking Model Scaling for Convolutional Neural Networks
0 2 4 6 8
FLOPS (Billions)
75
76
77
78
79
80
81ImageNet Top-1 Accuracy(%)
w=1.0
w=1.4
w=1.8
w=2.6
w=3.8
w=5.0
0 1 2 3 4
FLOPS (Billions)
75
76
77
78
79
80
81
d=1.0
d=2.0
d=3.0d=4.0
d=6.0 d=8.0
0 1 2 3
FLOPS (Billions)
75
76
77
78
79
80
81
r=1.0
r=1.3
r=1.5
r=1.7
r=1.9
r=2.2 r=2.5
Figure 3.Scaling Up a Baseline Model with Different Network Width ( w), Depth ( d), and Resolution ( r) Coefﬁcients. Bigger
networks with larger width, depth, or resolution tend to achieve higher accuracy, but the accuracy gain quickly saturate after reaching
80%, demonstrating the limitation of single dimension scaling. Baseline network is described in Table 1.
Tan et al., 2019) 2. As discussed in (Zagoruyko & Ko-
modakis, 2016), wider networks tend to be able to capture
more ﬁne-grained features and are easier to train. However,
extremely wide but shallow networks tend to have difﬁcul-
ties in capturing higher level features. Our empirical results
in Figure 3 (left) show that the accuracy quickly saturates
when networks become much wider with larger w.
Resolution (rrr): With higher resolution input images, Con-
vNets can potentially capture more ﬁne-grained patterns.
Starting from 224x224 in early ConvNets, modern Con-
vNets tend to use 299x299 (Szegedy et al., 2016) or 331x331
(Zoph et al., 2018) for better accuracy. Recently, GPipe
(Huang et al., 2018) achieves state-of-the-art ImageNet ac-
curacy with 480x480 resolution. Higher resolutions, such as
600x600, are also widely used in object detection ConvNets
(He et al., 2017; Lin et al., 2017). Figure 3 (right) shows the
results of scaling network resolutions, where indeed higher
resolutions improve accuracy, but the accuracy gain dimin-
ishes for very high resolutions (r= 1.0 denotes resolution
224x224 and r= 2.5 denotes resolution 560x560).
The above analyses lead us to the ﬁrst observation:
Observation 1 – Scaling up any dimension of network
width, depth, or resolution improves accuracy, but the accu-
racy gain diminishes for bigger models.
3.3. Compound Scaling
We empirically observe that different scaling dimensions are
not independent. Intuitively, for higher resolution images,
we should increase network depth, such that the larger re-
ceptive ﬁelds can help capture similar features that include
more pixels in bigger images. Correspondingly, we should
also increase network width when resolution is higher, in
2In some literature, scaling number of channels is called “depth
multiplier”, which means the same as our width coefﬁcient w.
0 5 10 15 20 25
FLOPS (billions)
76
77
78
79
80
81
82ImageNet Top1 Accuracy (%)
d=1.0, r=1.0
d=1.0, r=1.3
d=2.0, r=1.0
d=2.0, r=1.3
Figure 4.Scaling Network Width for Different Baseline Net-
works. Each dot in a line denotes a model with different width
coefﬁcient (w). All baseline networks are from Table 1. The ﬁrst
baseline network (d=1.0, r=1.0) has 18 convolutional layers with
resolution 224x224, while the last baseline (d=2.0, r=1.3) has 36
layers with resolution 299x299.
order to capture more ﬁne-grained patterns with more pixels
in high resolution images. These intuitions suggest that we
need to coordinate and balance different scaling dimensions
rather than conventional single-dimension scaling.
To validate our intuitions, we compare width scaling under
different network depths and resolutions, as shown in Figure
4. If we only scale network width w without changing
depth (d=1.0) and resolution (r=1.0), the accuracy saturates
quickly. With deeper (d=2.0) and higher resolution (r=2.0),
width scaling achieves much better accuracy under the same
FLOPS cost. These results lead us to the second observation:
Observation 2 – In order to pursue better accuracy and
efﬁciency, it is critical to balance all dimensions of network
width, depth, and resolution during ConvNet scaling.
EfﬁcientNet: Rethinking Model Scaling for Convolutional Neural Networks
In fact, a few prior work (Zoph et al., 2018; Real et al., 2019)
have already tried to arbitrarily balance network width and
depth, but they all require tedious manual tuning.
In this paper, we propose a newcompound scaling method,
which use a compound coefﬁcient φ to uniformly scales
network width, depth, and resolution in a principled way:
depth: d= αφ
width: w= βφ
resolution: r= γφ
s.t. α·β2 ·γ2 ≈2
α≥1,β ≥1,γ ≥1
(3)
where α,β,γ are constants that can be determined by a
small grid search. Intuitively, φis a user-speciﬁed coefﬁ-
cient that controls how many more resources are available
for model scaling, while α,β,γ specify how to assign these
extra resources to network width, depth, and resolution re-
spectively. Notably, the FLOPS of a regular convolution op
is proportional to d, w2, r2, i.e., doubling network depth
will double FLOPS, but doubling network width or resolu-
tion will increase FLOPS by four times. Since convolution
ops usually dominate the computation cost in ConvNets,
scaling a ConvNet with equation 3 will approximately in-
crease total FLOPS by
(
α·β2 ·γ2)φ
. In this paper, we
constraint α·β2 ·γ2 ≈2 such that for any new φ, the total
FLOPS will approximately3 increase by 2φ.
4. EfﬁcientNet Architecture
Since model scaling does not change layer operators ˆFi
in baseline network, having a good baseline network is
also critical. We will evaluate our scaling method using
existing ConvNets, but in order to better demonstrate the
effectiveness of our scaling method, we have also developed
a new mobile-size baseline, called EfﬁcientNet.
Inspired by (Tan et al., 2019), we develop our baseline net-
work by leveraging a multi-objective neural architecture
search that optimizes both accuracy and FLOPS. Speciﬁ-
cally, we use the same search space as (Tan et al., 2019),
and use ACC(m)×[FLOPS (m)/T]w as the optimization
goal, where ACC(m) and FLOPS (m) denote the accu-
racy and FLOPS of model m, T is the target FLOPS and
w=-0.07 is a hyperparameter for controlling the trade-off
between accuracy and FLOPS. Unlike (Tan et al., 2019;
Cai et al., 2019), here we optimize FLOPS rather than la-
tency since we are not targeting any speciﬁc hardware de-
vice. Our search produces an efﬁcient network, which we
name EfﬁcientNet-B0. Since we use the same search space
as (Tan et al., 2019), the architecture is similar to Mnas-
3FLOPS may differ from theoretical value due to rounding.
Table 1.EfﬁcientNet-B0 baseline network – Each row describes
a stage iwith ˆLi layers, with input resolution ⟨ ˆHi, ˆWi⟩ and output
channels ˆCi. Notations are adopted from equation 2.
Stage Operator Resolution#Channels#Layers
i ˆFi ˆHi×ˆWi ˆCi ˆLi
1 Conv3x3 224×224 32 1
2 MBConv1, k3x3 112×112 16 1
3 MBConv6, k3x3 112×112 24 2
4 MBConv6, k5x5 56×56 40 2
5 MBConv6, k3x3 28×28 80 3
6 MBConv6, k5x5 14×14 112 3
7 MBConv6, k5x5 14×14 192 4
8 MBConv6, k3x3 7×7 320 1
9 Conv1x1 & Pooling & FC7×7 1280 1
Net, except our EfﬁcientNet-B0 is slightly bigger due to
the larger FLOPS target (our FLOPS target is 400M). Ta-
ble 1 shows the architecture of EfﬁcientNet-B0. Its main
building block is mobile inverted bottleneck MBConv (San-
dler et al., 2018; Tan et al., 2019), to which we also add
squeeze-and-excitation optimization (Hu et al., 2018).
Starting from the baseline EfﬁcientNet-B0, we apply our
compound scaling method to scale it up with two steps:
• STEP 1: we ﬁrst ﬁx φ= 1, assuming twice more re-
sources available, and do a small grid search of α,β,γ
based on Equation 2 and 3. In particular, we ﬁnd
the best values for EfﬁcientNet-B0 are α= 1.2,β =
1.1,γ = 1.15, under constraint of α·β2 ·γ2 ≈2.
• STEP 2: we then ﬁx α,β,γ as constants and scale up
baseline network with different φusing Equation 3, to
obtain EfﬁcientNet-B1 to B7 (Details in Table 2).
Notably, it is possible to achieve even better performance by
searching for α,β,γ directly around a large model, but the
search cost becomes prohibitively more expensive on larger
models. Our method solves this issue by only doing search
once on the small baseline network (step 1), and then use
the same scaling coefﬁcients for all other models (step 2).
5. Experiments
In this section, we will ﬁrst evaluate our scaling method on
existing ConvNets and the new proposed EfﬁcientNets.
5.1. Scaling Up MobileNets and ResNets
As a proof of concept, we ﬁrst apply our scaling method
to the widely-used MobileNets (Howard et al., 2017; San-
dler et al., 2018) and ResNet (He et al., 2016). Table 3
shows the ImageNet results of scaling them in different
ways. Compared to other single-dimension scaling methods,
our compound scaling method improves the accuracy on all
these models, suggesting the effectiveness of our proposed
scaling method for general existing ConvNets.
EfﬁcientNet: Rethinking Model Scaling for Convolutional Neural Networks
Table 2. EfﬁcientNet Performance Results on ImageNet (Russakovsky et al., 2015). All EfﬁcientNet models are scaled from our
baseline EfﬁcientNet-B0 using different compound coefﬁcient φin Equation 3. ConvNets with similar top-1/top-5 accuracy are grouped
together for efﬁciency comparison. Our scaled EfﬁcientNet models consistently reduce parameters and FLOPS by an order of magnitude
(up to 8.4x parameter reduction and up to 16x FLOPS reduction) than existing ConvNets.
Model Top-1 Acc. Top-5 Acc. #Params Ratio-to-EfﬁcientNet#FLOPs Ratio-to-EfﬁcientNet
EfﬁcientNet-B0 77.1% 93.3% 5.3M 1x 0.39B 1x
ResNet-50 (He et al., 2016) 76.0% 93.0% 26M 4.9x 4.1B 11x
DenseNet-169 (Huang et al., 2017) 76.2% 93.2% 14M 2.6x 3.5B 8.9x
EfﬁcientNet-B1 79.1% 94.4% 7.8M 1x 0.70B 1x
ResNet-152 (He et al., 2016) 77.8% 93.8% 60M 7.6x 11B 16x
DenseNet-264 (Huang et al., 2017) 77.9% 93.9% 34M 4.3x 6.0B 8.6x
Inception-v3 (Szegedy et al., 2016) 78.8% 94.4% 24M 3.0x 5.7B 8.1x
Xception (Chollet, 2017) 79.0% 94.5% 23M 3.0x 8.4B 12x
EfﬁcientNet-B2 80.1% 94.9% 9.2M 1x 1.0B 1x
Inception-v4 (Szegedy et al., 2017) 80.0% 95.0% 48M 5.2x 13B 13x
Inception-resnet-v2 (Szegedy et al., 2017)80.1% 95.1% 56M 6.1x 13B 13x
EfﬁcientNet-B3 81.6% 95.7% 12M 1x 1.8B 1x
ResNeXt-101 (Xie et al., 2017) 80.9% 95.6% 84M 7.0x 32B 18x
PolyNet (Zhang et al., 2017) 81.3% 95.8% 92M 7.7x 35B 19x
EfﬁcientNet-B4 82.9% 96.4% 19M 1x 4.2B 1x
SENet (Hu et al., 2018) 82.7% 96.2% 146M 7.7x 42B 10x
NASNet-A (Zoph et al., 2018) 82.7% 96.2% 89M 4.7x 24B 5.7x
AmoebaNet-A (Real et al., 2019) 82.8% 96.1% 87M 4.6x 23B 5.5x
PNASNet (Liu et al., 2018) 82.9% 96.2% 86M 4.5x 23B 6.0x
EfﬁcientNet-B5 83.6% 96.7% 30M 1x 9.9B 1x
AmoebaNet-C (Cubuk et al., 2019) 83.5% 96.5% 155M 5.2x 41B 4.1x
EfﬁcientNet-B6 84.0% 96.8% 43M 1x 19B 1x
EfﬁcientNet-B7 84.3% 97.0% 66M 1x 37B 1x
GPipe (Huang et al., 2018) 84.3% 97.0% 557M 8.4x - -
We omit ensemble and multi-crop models (Hu et al., 2018), or models pretrained on 3.5B Instagram images (Mahajan et al., 2018).
Table 3. Scaling Up MobileNets and ResNet.
Model FLOPS Top-1 Acc.
Baseline MobileNetV1 (Howard et al., 2017)0.6B 70.6%
Scale MobileNetV1 by width (w=2) 2.2B 74.2%
Scale MobileNetV1 by resolution (r=2) 2.2B 72.7%
compound scale (ddd=1.4,www=1.2,rrr=1.3) 2.3B 75.6%
Baseline MobileNetV2 (Sandler et al., 2018)0.3B 72.0%
Scale MobileNetV2 by depth (d=4) 1.2B 76.8%
Scale MobileNetV2 by width (w=2) 1.1B 76.4%
Scale MobileNetV2 by resolution (r=2) 1.2B 74.8%
MobileNetV2 compound scale 1.3B 77.4%
Baseline ResNet-50 (He et al., 2016) 4.1B 76.0%
Scale ResNet-50 by depth (d=4) 16.2B 78.1%
Scale ResNet-50 by width (w=2) 14.7B 77.7%
Scale ResNet-50 by resolution (r=2) 16.4B 77.5%
ResNet-50 compound scale 16.7B 78.8%
Table 4. Inference Latency Comparison – Latency is measured
with batch size 1 on a single core of Intel Xeon CPU E5-2690.
Acc. @ Latency Acc. @ Latency
ResNet-152 77.8% @ 0.554s GPipe 84.3% @ 19.0s
EfﬁcientNet-B1 78.8% @ 0.098sEfﬁcientNet-B7 84.4% @ 3.1s
Speedup 5.7x Speedup 6.1x
0 5 10 15 20 25 30 35 40 45
FLOPS (Billions)
74
76
78
80
82
84Imagenet Top-1 Accuracy (%)
ResNet-34
ResNet-50
ResNet-152
DenseNet-201
Inception-v2
Inception-ResNet-v2
NASNet-A
NASNet-A
ResNeXt-101
Xception
AmeobaNet-A
AmoebaNet-C
SENet
B0
B3
B4
B5
EfﬁcientNet-B6
Top1 Acc. FLOPSResNet-152 (Xie et al., 2017)77.8% 11BEfﬁcientNet-B1 79.1% 0.7BResNeXt-101 (Xie et al., 2017)80.9% 32BEfﬁcientNet-B3 81.6% 1.8BSENet (Hu et al., 2018)82.7% 42BNASNet-A (Zoph et al., 2018)80.7% 24BEfﬁcientNet-B4 82.9% 4.2BAmeobaNet-C (Cubuk et al., 2019)83.5% 41BEfﬁcientNet-B5 83.6% 9.9B
Figure 5.FLOPS vs. ImageNet Accuracy – Similar to Figure 1
except it compares FLOPS rather than model size.
5.2. ImageNet Results for EfﬁcientNet
We train our EfﬁcientNet models on ImageNet using simi-
lar settings as (Tan et al., 2019): RMSProp optimizer with
decay 0.9 and momentum 0.9; batch norm momentum 0.99;
EfﬁcientNet: Rethinking Model Scaling for Convolutional Neural Networks
Table 5. EfﬁcientNet Performance Results on Transfer Learning Datasets. Our scaled EfﬁcientNet models achieve new state-of-the-
art accuracy for 5 out of 8 datasets, with 9.6x fewer parameters on average.
Comparison to best public-available results Comparison to best reported results
Model Acc. #Param Our Model Acc. #Param(ratio) Model Acc. #Param Our Model Acc. #Param(ratio)
CIFAR-10 NASNet-A 98.0% 85M EfﬁcientNet-B0 98.1% 4M (21x)†Gpipe99.0% 556M EfﬁcientNet-B7 98.9% 64M (8.7x)
CIFAR-100 NASNet-A 87.5% 85M EfﬁcientNet-B0 88.1% 4M (21x)Gpipe 91.3% 556M EfﬁcientNet-B791.7% 64M (8.7x)
Birdsnap Inception-v4 81.8% 41M EfﬁcientNet-B5 82.0% 28M (1.5x)GPipe 83.6% 556M EfﬁcientNet-B784.3% 64M (8.7x)
Stanford CarsInception-v4 93.4% 41M EfﬁcientNet-B3 93.6% 10M (4.1x)‡DAT 94.8% - EfﬁcientNet-B7 94.7% -
Flowers Inception-v4 98.5% 41M EfﬁcientNet-B5 98.5% 28M (1.5x)DAT 97.7% - EfﬁcientNet-B7 98.8% -
FGVC AircraftInception-v4 90.9% 41M EfﬁcientNet-B3 90.7% 10M (4.1x)DAT 92.9% - EfﬁcientNet-B7 92.9% -
Oxford-IIIT PetsResNet-152 94.5% 58M EfﬁcientNet-B4 94.8% 17M (5.6x)GPipe 95.9% 556M EfﬁcientNet-B6 95.4% 41M (14x)
Food-101 Inception-v4 90.8% 41M EfﬁcientNet-B4 91.5% 17M (2.4x)GPipe 93.0% 556M EfﬁcientNet-B793.0% 64M (8.7x)
Geo-Mean (4.7x) (9.6x)
†GPipe (Huang et al., 2018) trains giant models with specialized pipeline parallelism library.
‡DAT denotes domain adaptive transfer learning (Ngiam et al., 2018). Here we only compare ImageNet-based transfer learning results.
Transfer accuracy and #params for NASNet (Zoph et al., 2018), Inception-v4 (Szegedy et al., 2017), ResNet-152 (He et al., 2016) are from (Kornblith et al., 2019).
0.0 0.2 0.4 0.6 0.8 1.0
Number of Parameters (Millions, log-scale)
        """
    )

    chunks = split_text(raw_text)
    print(f"Total chunks: {len(chunks)}")
    print(f"Configured chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP}")
    if chunks:
        lengths = [len(chunk) for chunk in chunks]
        print(f"Chunk length: min={min(lengths)}, max={max(lengths)}, avg={sum(lengths) // len(lengths)}")
    print("Adjacent overlap lengths:")
    for i in range(len(chunks) - 1):
        print(f"  {i + 1:02d} -> {i + 2:02d}: {_shared_overlap_len(chunks[i], chunks[i + 1])} chars")
    print()
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Chunk {i} ---")
        print(chunk)
        print()


if __name__ == "__main__":
    main()
