"""
Piste CNN — Classification de l'état d'un bien à partir de ses photos.

Architecture suggérée : ResNet-18 ou EfficientNet-B0 fine-tuné
sur vos photos labellisées (minimum 200 par classe recommandé).

Structure du dataset attendue :
    data/photos/
    ├── excellent/
    ├── bon/
    ├── correct/
    └── a_renover/
"""
# TODO : choisir entre torchvision (PyTorch) ou tensorflow/keras
# Exemple avec PyTorch :
#
# from torchvision import models, transforms
# import torch.nn as nn
#
# def build_model(num_classes=4):
#     model = models.resnet18(pretrained=True)
#     model.fc = nn.Linear(model.fc.in_features, num_classes)
#     return model
#
# def train(data_dir, epochs=10, lr=1e-4):
#     ...
#
# def predict(image_path: str) -> dict:
#     ...

raise NotImplementedError("À implémenter par l'équipe R&D Vision")
