# clone official repositories
#低光照
#git clone git@github.com:aaaaangel/RRDNet.git executor/brightening/tools/RRDNet
#去模糊
# git clone git@github.com:lingyanruan/DRBNet.git executor/defocus_deblurring/tools/DRBNet
#git clone git@github.com:codeslake/IFAN.git executor/defocus_deblurring/tools/IFAN
#git clone git@github.com:swz30/Restormer.git executor/defocus_deblurring/tools/Restormer############用于多个
#去雨
#restormer
#git clone https://github.com/cschenxiang/NeRD-Rain.git executor/deraining/tools/NeRD-Rain
#去雾
#git clone git@github.com:IDKiro/DehazeFormer.git executor/dehazing/tools/DehazeFormer
#git clone git@github.com:google-research/maxim.git executor/dehazing/tools/maxim###################用于多个
#git clone https://github.com/xiaofeng94/RefineDNet-for-dehazing.git executor/dehazing/tools/RefineDNet
#去噪
#git clone git@github.com:swz30/MPRNet.git  executor/denoising/tools/MPRNet
#git clone git@github.com:JingyunLiang/SwinIR.git executor/denoising/tools/SwinIR
#j降质
#git clone git@github.com:jiaxi-jiang/FBCNN.git executor/jpeg_compression_artifact_removal/tools/FBCNN
#超分辨率
#git clone git@github.com:XPixelGroup/HAT.git executor/super_resolution/tools/HAT
#git clone git@github.com:XPixelGroup/DiffBIR.git executor/super_resolution/tools/DiffBIR

cd executor/super_resolution/tools/DiffBIR
git checkout 7bd5675
cd ../../../..

# prepare custom scripts to adapt to our framework
#去模糊
#mv installation/custom_tool_scripts/drbnet_run.py executor/defocus_deblurring/tools/DRBNet/run.py
#去雾
#mv installation/custom_tool_scripts/dehazeformer_inference.py executor/dehazing/tools/DehazeFormer/inference.py
#降噪
#mv installation/custom_tool_scripts/swinir_inference.py executor/denoising/tools/SwinIR/inference.py
#j降质
#mv installation/custom_tool_scripts/fbcnn_inference.py executor/jpeg_compression_artifact_removal/tools/FBCNN/inference.py
#超分辨率
#mv installation/custom_tool_scripts/hat_inference.py executor/super_resolution/tools/HAT/hat/inference.py

# some repos are used for multiple single-degradation restorations tasks; use symlinks to save space
#ln -s $(pwd)/executor/dehazing/tools/maxim executor/denoising/tools/
#ln -s $(pwd)/executor/defocus_deblurring/tools/Restormer executor/denoising/tools/

#ln -s $(pwd)/executor/dehazing/tools/maxim executor/deraining/tools/
#ln -s $(pwd)/executor/defocus_deblurring/tools/Restormer executor/deraining/tools/

#ln -s $(pwd)/executor/denoising/tools/SwinIR executor/jpeg_compression_artifact_removal/tools/


#ln -s $(pwd)/executor/denoising/tools/SwinIR executor/super_resolution/tools/
