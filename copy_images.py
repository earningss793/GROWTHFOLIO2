import os
import shutil

# 이미지 매핑 정의
image_mapping = {
    "2.jpg": "core_competency.jpg",
    "3.jpg": "service_campaign.jpg",
    "13.jpg": "retargeting1.jpg",
    "14.jpg": "retargeting2.jpg",
    "21.png": "armypedia.jpg",
    "Slide 55.png": "sns_operation.jpg",
    "Slide 544.png": "seo_project.jpg"
}

# static/images 디렉토리 생성
os.makedirs("static/images", exist_ok=True)

# 이미지 복사
for src_name, dst_name in image_mapping.items():
    src_path = os.path.join("attached_assets", src_name)
    dst_path = os.path.join("static/images", dst_name)
    try:
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            print(f"Copied {src_name} to {dst_name}")
        else:
            print(f"Source file not found: {src_path}")
    except Exception as e:
        print(f"Error copying {src_name}: {str(e)}")