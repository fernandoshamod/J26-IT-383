# Models, datasets and evaluation scope

U-Net V3: segmentation_models_pytorch U-Net / ResNet18, retained four structural classes room_region, wall, door, window. Subset 320/64/64 (448 total), 16 epochs; native diagnostic mIoU approximately 0.79046. No independent real-venue metric geometry validation follows from this number. Checkpoint SHA-256 352631590f1610b6b29341b3d1c59fad2ad564ed07fa4b77c9c59470bfde5c0c.

Opening YOLO V3: door/window; publisher-native mAP50 approximately 0.75475. External CVC door result TP=1, FP=68, FN=85 demonstrates domain shift; do not hide it behind the native metric. Checkpoint SHA-256 64c8d7a0d205362f174871ca861cfa80ff24d2ff1d2a191505dad2688e67abc7.

Event-object YOLO V2: twelve synthetic diagram classes, mAP50 approximately 0.91045 on that synthetic task. Real event-stock inventory is not validated. Checkpoint SHA-256 878cabdfafd70544fbcda8154fd80d1007270c00940d699b9b7b340e2afb1a6a.

Chair-only pilot: published-label AP50 approximately 0.83951; incomplete labels and unresolved underlying image rights prevent an all-chair inventory claim. Experimental and disabled by default.

Evidence sources: COMPONENT_1_PP1_COLAB_DELIVERY_V1/MODEL_REGISTRY.json and 03_DATASET_EVIDENCE/ALL_MODEL_RIGHTS_AND_SCOPE.md in preserved workspace. Notebook outputs removed from public staging; actual datasets/checkpoints remain private. Native/held-out/synthetic/domain-shift metrics are different tasks and cannot be averaged as one accuracy. New five-class U-Net attempt failed qualification; retained V3 remains authoritative. No retraining, model promotion or remote Colab execution was performed in this audit.
