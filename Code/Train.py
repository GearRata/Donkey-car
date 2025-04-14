import os
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import GlobalAveragePooling2D, Dense, Dropout
from tensorflow.keras import regularizers

# Local paths
image_dir = r'C:\Users\User\Downloads\room1'  # เปลี่ยนเส้นทางตามที่คุณต้องการ
csv_file = r'C:\Users\User\Downloads\room1.csv'  # เปลี่ยนเส้นทางตามที่คุณต้องการ

# Load dataset
data = pd.read_csv(csv_file)
data['image_path'] = data['Image'].apply(lambda x: os.path.join(image_dir, x))
data = data[['image_path', 'Steering', 'Left_Speed', 'Right_Speed']]

# Split data into training and validation sets
train_data, val_data = train_test_split(data, test_size=0.2, random_state=42)

# Data Augmentation
data_augmentation = tf.keras.Sequential([
    tf.keras.layers.RandomFlip("horizontal"),
    tf.keras.layers.RandomRotation(0.1),
    tf.keras.layers.RandomContrast(0.2)
])

# Preprocessing function
def load_and_preprocess_image(image_path, steering, left_speed, right_speed):
    image = tf.io.read_file(image_path)
    image = tf.image.decode_jpeg(image, channels=3)
    image = tf.image.resize(image, (224, 224))
    image = tf.keras.applications.mobilenet_v2.preprocess_input(image)  # ใช้การ preprocess ของ MobileNetV2
    labels = tf.convert_to_tensor([steering, left_speed, right_speed], dtype=tf.float32)
    return image, labels

def create_dataset(dataframe, batch_size=8, augment=False):
    dataset = tf.data.Dataset.from_tensor_slices((dataframe['image_path'].values,
                                                   dataframe['Steering'].values,
                                                   dataframe['Left_Speed'].values,
                                                   dataframe['Right_Speed'].values))
    dataset = dataset.map(load_and_preprocess_image, num_parallel_calls=tf.data.AUTOTUNE)
    if augment:
        dataset = dataset.map(lambda x, y: (data_augmentation(x, training=True), y), num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.shuffle(buffer_size=500).batch(batch_size).prefetch(buffer_size=tf.data.AUTOTUNE)
    return dataset

# Create datasets
batch_size = 16  # ใช้ขนาดที่ใหญ่ขึ้นเพื่อเพิ่มประสิทธิภาพ
train_dataset = create_dataset(train_data, batch_size, augment=True)
val_dataset = create_dataset(val_data, batch_size, augment=False)

# โหลดโมเดล MobileNetV2 จาก Keras (ไม่ใช้ TensorFlow Hub)
base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224, 224, 3))

# สร้างโมเดล
model = tf.keras.Sequential([
    base_model,
    GlobalAveragePooling2D(),
    Dense(128, activation='relu', kernel_regularizer=regularizers.l2(0.01)),
    Dropout(0.5),  # ใช้ Dropout เพิ่มเติมเพื่อช่วยลด overfitting
    Dense(3)  # Output: [steering, left_speed, right_speed]
])

# คอมไพล์โมเดล
model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss='mse', metrics=['mae'])

# Callbacks
early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, min_lr=1e-7)
model_checkpoint = ModelCheckpoint('best_model.h5', save_best_only=True, monitor='val_loss', mode='min')

# ฝึกโมเดล
history = model.fit(
    train_dataset,
    validation_data=val_dataset,
    epochs=50,  # เพิ่มจำนวน epochs
    callbacks=[early_stopping, reduce_lr, model_checkpoint]
)

# บันทึกโมเดลที่ฝึกเสร็จแล้ว
saved_model_dir = r'C:\path\to\save\final_model_saved'  # เปลี่ยนเส้นทางตามที่ต้องการ
model.save(saved_model_dir)

# แปลงเป็น TFLite
converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
converter.optimizations = [tf.lite.Optimize.DEFAULT]  # เปิดใช้งานการปรับแต่ง
tflite_model = converter.convert()

# บันทึกโมเดล TFLite
tflite_model_path = r'C:\path\to\save\mobilenetv2_lane_detection roomnew.tflite'  # เปลี่ยนเส้นทางตามที่ต้องการ
with open(tflite_model_path, 'wb') as f:
    f.write(tflite_model)

print("โมเดล TFLite ถูกบันทึกที่:", tflite_model_path)
