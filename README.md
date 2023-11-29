# Домашняя работа по ВВОТ 
## Сделал Юсупов Марсель 11-002


### Для запуска необходимо 

1. `git clone https://github.com/MarselYsup/vvot47.git`
2. `cd vvot47`
2. `yc iam service-account create --name  {servoce-account-name} --folder-name {folder-name}`
3. `yc resource-manager folder add-access-binding {folder-name} --role admin --service-account-name {servoce-account-name}`
4. `yc iam service-account get {servoce-account-name}`
5. `yc iam key create --service-account-id {service-account-id} --folder-name {folder-name} --output key.json`
6. `yc iam create-token`
7. `terraform init`
8. `terraform apply`

! Для удаления можно использовать `terraform destroy`

### Необходимо ввести для запуска следующие параметры

1. `admin_id` - ID админской учетки (получить можно при помощи команды `yc iam service-account get {servoce-account-name}`)
2. `cloud_id` - ID облака (получить можно при помощи команды  `yc resource-manager cloud get itis-vvot`)
3. `folder_id` - ID folder (получить можно при помощи команды `yc resource-manager folder get {folder-name}`)
4. `iam_token` - IAM токен (получить можно при помощи команды `yc iam create-token`)
5. `tgkey` - Телеграмм ключ -(получить можно вызвав https://t.me/BotFather с командой `/newbot` )

### Важно!

1. Прогрев Триггеров, Базы и очереди может занимать в среднем 3-5 минут (пожалуйста подождите время, чтобы не нарушить процесс отпарвки)
2. Для бота можно вызвать три команды - `/getface`, `/find {name}`,  `/help`
3. Код написан на языке 'Python'
4. В домашней работе не использовались контейнеры, поэтому реестр для Docker файлов не понадобился
5. Вся домашняя работа сделана на Яндекс Функциях

### Структура проекта

1. `/boot` - Директория с файлами для запуски и работы бота
2. `/face-cut` - Директория с файлами для вырезания лиц 
3. `/face-detection` - Директория с файлами обнаружения лиц с помощью API VISION
4. `main.tf` - основной терраформ файл, по необходимости можно подкоректировать ресурсы
5. `variables.tf` - переменные для ввода перед запуском 