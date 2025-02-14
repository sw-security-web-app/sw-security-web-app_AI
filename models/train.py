import os
import numpy as np
from datasets import Dataset
from evaluate import load as load_metric
from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
import torch

MODEL_VERSION = "version_0.2"
class ModelTrainer:
    def __init__(self, base_dir, preprocessed_data_path, model_save_path, model_name="bert-base-uncased", num_labels=2):
        self.BASE_DIR = base_dir
        self.PREPROCESSED_DATA_PATH = preprocessed_data_path
        self.MODEL_SAVE_PATH = model_save_path
        self.MODEL_NAME = model_name
        self.NUM_LABELS = num_labels

        self.model = BertForSequenceClassification.from_pretrained(self.MODEL_NAME, num_labels=self.NUM_LABELS)
        self.tokenizer = BertTokenizer.from_pretrained(self.MODEL_NAME)

        self.dataset = self.load_dataset()
        self.train_dataset = None
        self.eval_dataset = None

    def load_dataset(self):
        print(f"{self.PREPROCESSED_DATA_PATH}")
        dataset_path = os.path.join(self.PREPROCESSED_DATA_PATH)
        dataset = Dataset.load_from_disk(dataset_path)
        print("Successfully load dataset")
        return dataset

    def tokenize_data(self):
        def tokenize_function(examples):
            return self.tokenizer(examples["text"], padding="max_length", truncation=True, max_length=297)
        
        tokenized_datasets = self.dataset.map(tokenize_function, batched=True)
        self.train_dataset, self.eval_dataset = tokenized_datasets.train_test_split(test_size=0.2, seed=42).values()

    def set_training_args(self):
        # trainer 하이퍼파라미터 설정
        return  TrainingArguments(
                    save_strategy="no",
                    output_dir=os.path.join(self.BASE_DIR, "results"),    
                    num_train_epochs=2,                                   
                    per_device_train_batch_size=16,                       
                    per_device_eval_batch_size=64,                       
                    warmup_steps=500,                                     
                    weight_decay=0.01,                                    
                    logging_dir=os.path.join(self.BASE_DIR, "models", "basemodel", MODEL_VERSION, "logs"),      
                    logging_steps=10,
                    evaluation_strategy="epoch",                          
                )
    
    def compute_metrics(self, eval_pred):
        metric_acc = load_metric("accuracy")
        metric_prec = load_metric("precision")
        metric_rec = load_metric("recall")
        metric_f1 = load_metric("f1")

        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)

        acc = metric_acc.compute(predictions=predictions, references=labels)
        prec = metric_prec.compute(predictions=predictions, references=labels, average="binary")
        rec = metric_rec.compute(predictions=predictions, references=labels, average="binary")
        f1 = metric_f1.compute(predictions=predictions, references=labels, average="binary")

        return {
            "accuracy": acc["accuracy"],
            "precision": prec["precision"],
            "recall": rec["recall"],
            "f1-score": f1["f1"]
        }

    def train(self):
        self.tokenize_data()

        training_args = self.set_training_args()

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=self.train_dataset,
            eval_dataset=self.eval_dataset,
            compute_metrics=self.compute_metrics  
        )

        # 모델 훈련
        trainer.train()

# 모델 저장
    def save_model(self):
        os.makedirs(self.MODEL_SAVE_PATH, exist_ok=True)
        self.model.save_pretrained(self.MODEL_SAVE_PATH)
        self.tokenizer.save_pretrained(self.MODEL_SAVE_PATH)
        print(f"Succesfully saved model and tokenizer in {self.MODEL_SAVE_PATH}")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREPROCESSED_DATA_PATH = os.path.join(BASE_DIR, "data", "preprocessed", "preprocessed_pii_data.arrow")
MODEL_SAVE_PATH = os.path.join(BASE_DIR, 'models', 'basemodel', MODEL_VERSION)

trainer = ModelTrainer(BASE_DIR, PREPROCESSED_DATA_PATH, MODEL_SAVE_PATH)
trainer.train()
trainer.save_model( )