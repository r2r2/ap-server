-- upgrade --
CREATE TABLE IF NOT EXISTS "claimway" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "claimway" IS 'Маршрут согласования заявки';
CREATE TABLE IF NOT EXISTS "enablescope" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(64) NOT NULL
);
COMMENT ON COLUMN "enablescope"."name" IS 'Название роута';
COMMENT ON TABLE "enablescope" IS 'Доступные роли для конкретного роута';
CREATE TABLE IF NOT EXISTS "parking" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255),
    "max_places" SMALLINT NOT NULL
);
COMMENT ON COLUMN "parking"."name" IS 'Название парковки(гостевая/частная...)';
COMMENT ON COLUMN "parking"."max_places" IS 'Общее количество парковочных мест';
COMMENT ON TABLE "parking" IS 'Вся парковка';
CREATE TABLE IF NOT EXISTS "parkingplace" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "real_number" SMALLINT NOT NULL,
    "parking_id" INT NOT NULL REFERENCES "parking" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "parkingplace"."real_number" IS 'Номер парковочного места';
COMMENT ON TABLE "parkingplace" IS 'Парковочное место';
CREATE TABLE IF NOT EXISTS "pass" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "rfid" BIGINT,
    "pass_type" VARCHAR(64) NOT NULL,
    "valid_till_date" TIMESTAMPTZ NOT NULL,
    "valid" BOOL NOT NULL  DEFAULT True
);
CREATE INDEX IF NOT EXISTS "idx_pass_rfid_e5e25d" ON "pass" ("rfid");
COMMENT ON COLUMN "pass"."pass_type" IS 'Тип пропуска (бумажный/карта/лицо)';
COMMENT ON COLUMN "pass"."valid_till_date" IS 'До какого числа действует пропуск';
COMMENT ON COLUMN "pass"."valid" IS 'Пропуск действителен?';
COMMENT ON TABLE "pass" IS 'Пропуск';
CREATE TABLE IF NOT EXISTS "claim" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "pass_type" VARCHAR(64) NOT NULL,
    "approved" BOOL NOT NULL  DEFAULT False,
    "claim_way_approved" BOOL,
    "claim_way_2_notified" BOOL,
    "is_in_blacklist" BOOL NOT NULL  DEFAULT False,
    "pnd_agreement" BOOL NOT NULL  DEFAULT False,
    "information" VARCHAR(255),
    "status" VARCHAR(128) NOT NULL,
    "claim_way_id" INT REFERENCES "claimway" ("id") ON DELETE CASCADE,
    "claim_way_2_id" INT REFERENCES "claimway" ("id") ON DELETE CASCADE,
    "pass_id_id" INT REFERENCES "pass" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_claim_pass_id_6c2a07" ON "claim" ("pass_id_id");
COMMENT ON COLUMN "claim"."pass_type" IS 'Тип пропуска (разовый/временный/материальный)';
COMMENT ON COLUMN "claim"."approved" IS 'Заявка одобрена?';
COMMENT ON COLUMN "claim"."claim_way_approved" IS 'Основной маршрут согласования';
COMMENT ON COLUMN "claim"."claim_way_2_notified" IS 'Отправить оповещение второму маршруту';
COMMENT ON COLUMN "claim"."is_in_blacklist" IS 'В черном списке?';
COMMENT ON COLUMN "claim"."pnd_agreement" IS 'Согласие на обработку ПНД';
COMMENT ON COLUMN "claim"."information" IS 'Любая информация о заявке';
COMMENT ON COLUMN "claim"."status" IS 'Статус заявки(действующая/отработана/просрочена)';
COMMENT ON TABLE "claim" IS 'Заявка на пропуск';
CREATE TABLE IF NOT EXISTS "claimtozone" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "claim_id" INT NOT NULL REFERENCES "claim" ("id") ON DELETE CASCADE,
    "pass_id_id" INT REFERENCES "pass" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_claimtozone_claim_i_d4f006" ON "claimtozone" ("claim_id");
COMMENT ON TABLE "claimtozone" IS 'Заявка на посещение конкретной зоны';
CREATE TABLE IF NOT EXISTS "plugin" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "filename" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "enabled" BOOL NOT NULL  DEFAULT False
);
CREATE TABLE IF NOT EXISTS "role" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255) NOT NULL
);
COMMENT ON COLUMN "role"."name" IS 'Название роли';
COMMENT ON TABLE "role" IS 'Роли пользователей для согласований';
CREATE TABLE IF NOT EXISTS "systemsettings" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "claimway_before_n_minutes" SMALLINT NOT NULL  DEFAULT 60,
    "max_systemuser_license" SMALLINT NOT NULL  DEFAULT 100,
    "max_photo_upload" SMALLINT NOT NULL  DEFAULT 10,
    "watermark_transparency" SMALLINT NOT NULL  DEFAULT 128,
    "watermark_format" VARCHAR(10) NOT NULL  DEFAULT 'PNG',
    "watermark_font_size" SMALLINT NOT NULL  DEFAULT 24,
    "watermark_font_type" VARCHAR(32) NOT NULL  DEFAULT 'FreeMono.ttf',
    "watermark_font_rgb_color" VARCHAR(14) NOT NULL  DEFAULT '80,0,0',
    "days_before_archive" SMALLINT NOT NULL  DEFAULT 60,
    "max_parking_time_hours" SMALLINT NOT NULL  DEFAULT 8,
    "parking_timeslot_interval" SMALLINT NOT NULL  DEFAULT 0
);
COMMENT ON COLUMN "systemsettings"."claimway_before_n_minutes" IS 'Кол-во минут до отправки напоминания о согласовании заявки';
COMMENT ON COLUMN "systemsettings"."max_systemuser_license" IS 'Кол-во пользовательских лицензий';
COMMENT ON COLUMN "systemsettings"."max_photo_upload" IS 'Кол-во загружаемых за раз фото';
COMMENT ON COLUMN "systemsettings"."watermark_transparency" IS 'Прозрачность водяного знака от 0...255';
COMMENT ON COLUMN "systemsettings"."watermark_format" IS 'Формат сохранения изображения с водяным знаком';
COMMENT ON COLUMN "systemsettings"."watermark_font_size" IS 'Размер шрифта водяного знака';
COMMENT ON COLUMN "systemsettings"."watermark_font_type" IS 'Тип шрифта';
COMMENT ON COLUMN "systemsettings"."watermark_font_rgb_color" IS 'RGB цвет';
COMMENT ON COLUMN "systemsettings"."days_before_archive" IS 'Кол-во дней после которых данные архивируются.';
COMMENT ON COLUMN "systemsettings"."max_parking_time_hours" IS 'Максимально допустимое время нахождения гостевого автомобиля на парковке.';
COMMENT ON COLUMN "systemsettings"."parking_timeslot_interval" IS 'Интервал в минутах для бронирования машиноместа на парковке.';
COMMENT ON TABLE "systemsettings" IS 'Настройки программы';
CREATE TABLE IF NOT EXISTS "systemuser" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "deleted" BOOL NOT NULL  DEFAULT False,
    "first_name" VARCHAR(36) NOT NULL,
    "last_name" VARCHAR(36) NOT NULL,
    "middle_name" VARCHAR(36),
    "username" VARCHAR(36) NOT NULL UNIQUE,
    "password" TEXT NOT NULL,
    "salt" TEXT NOT NULL,
    "last_login" TIMESTAMPTZ,
    "last_logout" TIMESTAMPTZ,
    "expire_session_delta" INT NOT NULL  DEFAULT 86400,
    "phone" VARCHAR(24),
    "email" VARCHAR(36),
    "cabinet_number" VARCHAR(12),
    "department_name" VARCHAR(255)
);
CREATE INDEX IF NOT EXISTS "idx_systemuser_usernam_c3bed3" ON "systemuser" ("username");
CREATE INDEX IF NOT EXISTS "idx_systemuser_phone_2ca695" ON "systemuser" ("phone");
CREATE INDEX IF NOT EXISTS "idx_systemuser_email_11a1a8" ON "systemuser" ("email");
COMMENT ON COLUMN "systemuser"."first_name" IS 'Имя';
COMMENT ON COLUMN "systemuser"."last_name" IS 'Фамилия';
COMMENT ON COLUMN "systemuser"."middle_name" IS 'Отчество';
COMMENT ON COLUMN "systemuser"."cabinet_number" IS 'Номер кабинета';
COMMENT ON COLUMN "systemuser"."department_name" IS 'Название отдела';
COMMENT ON TABLE "systemuser" IS 'Сотрудник компании';
CREATE TABLE IF NOT EXISTS "activedir" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "sid" VARCHAR(128),
    "user_id" INT NOT NULL REFERENCES "systemuser" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "activedir"."sid" IS 'SID пользователя';
COMMENT ON TABLE "activedir" IS 'Данные пользователя из Active Directory';
CREATE TABLE IF NOT EXISTS "claimwayapproval" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "approved" BOOL,
    "comment" VARCHAR(255),
    "claim_id" INT NOT NULL REFERENCES "claim" ("id") ON DELETE CASCADE,
    "system_user_id" INT NOT NULL REFERENCES "systemuser" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "claimwayapproval"."approved" IS 'Заявка одобрена?';
COMMENT ON COLUMN "claimwayapproval"."comment" IS 'Причина отказа или любой комментарий.';
COMMENT ON TABLE "claimwayapproval" IS 'Одобрение заявки в процессе согласования';
CREATE TABLE IF NOT EXISTS "pushsubscription" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "subscription_info" JSONB NOT NULL,
    "system_user_id" INT NOT NULL REFERENCES "systemuser" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_pushsubscri_system__018e8b" ON "pushsubscription" ("system_user_id");
COMMENT ON COLUMN "pushsubscription"."subscription_info" IS 'Информация для отправки push-сообщений этому пользователю';
COMMENT ON TABLE "pushsubscription" IS 'Web Push подписка';
CREATE TABLE IF NOT EXISTS "strangerthings" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "fio_changed" JSONB,
    "data_changed" JSONB,
    "pass_to_black_list" JSONB,
    "claim_way_changed" JSONB,
    "max_parking_time_hours" JSONB,
    "system_user_id" INT NOT NULL REFERENCES "systemuser" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_strangerthi_system__e90110" ON "strangerthings" ("system_user_id");
COMMENT ON COLUMN "strangerthings"."fio_changed" IS 'изменение ФИО посетителя при выдаче пропуска';
COMMENT ON COLUMN "strangerthings"."data_changed" IS 'редактирование данных посетителя после его визита';
COMMENT ON COLUMN "strangerthings"."pass_to_black_list" IS 'оформление пропуска на посетителя из ''ЧС''';
COMMENT ON COLUMN "strangerthings"."claim_way_changed" IS 'изменение маршрутов заявок';
COMMENT ON COLUMN "strangerthings"."max_parking_time_hours" IS 'Превышено максимально допустимое время нахождения гостевого автомобиля на парковке';
COMMENT ON TABLE "strangerthings" IS 'Подозрительные события';
CREATE TABLE IF NOT EXISTS "systemusersession" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "expire_time" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    "logout_time" TIMESTAMPTZ,
    "user_agent" TEXT,
    "salt" TEXT NOT NULL,
    "nonce" TEXT NOT NULL,
    "tag" TEXT NOT NULL,
    "user_id" INT REFERENCES "systemuser" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "systemusersession" IS 'Данные сессии сотрудника компании';
CREATE TABLE IF NOT EXISTS "transport" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "model" VARCHAR(16),
    "number" VARCHAR(16) NOT NULL UNIQUE,
    "color" VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS "idx_transport_number_f907b8" ON "transport" ("number");
COMMENT ON COLUMN "transport"."number" IS 'Регистрационный номер';
COMMENT ON COLUMN "transport"."color" IS 'Цвет';
COMMENT ON TABLE "transport" IS 'Данные транспорта';
CREATE TABLE IF NOT EXISTS "parkingtimeslot" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "start" TIMESTAMPTZ NOT NULL,
    "end" TIMESTAMPTZ NOT NULL,
    "timeslot" VARCHAR(32),
    "parking_place_id" INT NOT NULL REFERENCES "parkingplace" ("id") ON DELETE CASCADE,
    "transport_id" INT NOT NULL REFERENCES "transport" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "parkingtimeslot"."timeslot" IS 'Время резерва парковочного места.';
COMMENT ON TABLE "parkingtimeslot" IS 'Парковочные временные слоты';
CREATE TABLE IF NOT EXISTS "visitorphoto" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "signature" JSONB,
    "webcam_img" BYTEA,
    "scan_img" BYTEA,
    "car_number_img" BYTEA,
    "add_watermark_image" BOOL   DEFAULT False,
    "add_watermark_text" BOOL   DEFAULT False,
    "watermark_id" INT,
    "watermark_position" VARCHAR(11),
    "watermark_width" SMALLINT,
    "watermark_height" SMALLINT
);
COMMENT ON COLUMN "visitorphoto"."webcam_img" IS 'Фото с веб-камеры';
COMMENT ON COLUMN "visitorphoto"."scan_img" IS 'Скан документа';
COMMENT ON COLUMN "visitorphoto"."car_number_img" IS 'Фото номера транспорта';
COMMENT ON COLUMN "visitorphoto"."watermark_position" IS 'Позиция водяного знака на картинке';
COMMENT ON COLUMN "visitorphoto"."watermark_width" IS 'Ширина водяного знака';
COMMENT ON COLUMN "visitorphoto"."watermark_height" IS 'Высота водяного знака';
COMMENT ON TABLE "visitorphoto" IS 'Фото посетителя';
CREATE TABLE IF NOT EXISTS "drivelicense" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "date_of_issue" DATE,
    "expiration_date" DATE,
    "place_of_issue" VARCHAR(255),
    "address_of_issue" VARCHAR(255),
    "number" BIGINT NOT NULL UNIQUE,
    "categories" VARCHAR(16),
    "photo_id" INT  UNIQUE REFERENCES "visitorphoto" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_drivelicens_number_9e56f0" ON "drivelicense" ("number");
CREATE INDEX IF NOT EXISTS "idx_drivelicens_photo_i_d8934e" ON "drivelicense" ("photo_id");
COMMENT ON COLUMN "drivelicense"."date_of_issue" IS 'Дата выдачи водительского удостоверения';
COMMENT ON COLUMN "drivelicense"."expiration_date" IS 'Дата окончания действия водительского удостоверения';
COMMENT ON COLUMN "drivelicense"."place_of_issue" IS 'Орган выдавший водительское удостоверение';
COMMENT ON COLUMN "drivelicense"."address_of_issue" IS 'Регион, где было выдано водительское удостоверение';
COMMENT ON COLUMN "drivelicense"."number" IS 'Номер водительского удостоверения';
COMMENT ON COLUMN "drivelicense"."categories" IS 'Открытые категории';
COMMENT ON TABLE "drivelicense" IS 'Водительское удостоверение';
CREATE TABLE IF NOT EXISTS "internationalpassport" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "number" BIGINT NOT NULL UNIQUE,
    "date_of_birth" DATE,
    "date_of_issue" DATE,
    "photo_id" INT  UNIQUE REFERENCES "visitorphoto" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_internation_number_6cc263" ON "internationalpassport" ("number");
CREATE INDEX IF NOT EXISTS "idx_internation_photo_i_ba2ac2" ON "internationalpassport" ("photo_id");
COMMENT ON COLUMN "internationalpassport"."number" IS 'Номер паспорта';
COMMENT ON COLUMN "internationalpassport"."date_of_birth" IS 'Дата рождения';
COMMENT ON COLUMN "internationalpassport"."date_of_issue" IS 'Дата выдачи';
COMMENT ON TABLE "internationalpassport" IS 'Заграничный паспорт';
CREATE TABLE IF NOT EXISTS "militaryid" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "number" VARCHAR(16) NOT NULL,
    "date_of_birth" DATE,
    "place_of_issue" VARCHAR(255),
    "date_of_issue" DATE,
    "place_of_birth" VARCHAR(255),
    "photo_id" INT  UNIQUE REFERENCES "visitorphoto" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_militaryid_number_d87aca" ON "militaryid" ("number");
CREATE INDEX IF NOT EXISTS "idx_militaryid_photo_i_0ddd4e" ON "militaryid" ("photo_id");
COMMENT ON COLUMN "militaryid"."number" IS 'Номер военного билета';
COMMENT ON COLUMN "militaryid"."date_of_birth" IS 'Дата рождения';
COMMENT ON COLUMN "militaryid"."place_of_issue" IS 'Орган выдавший военный билет';
COMMENT ON COLUMN "militaryid"."date_of_issue" IS 'Дата выдачи военного билета';
COMMENT ON COLUMN "militaryid"."place_of_birth" IS 'Место рождения';
COMMENT ON TABLE "militaryid" IS 'Военный билет';
CREATE TABLE IF NOT EXISTS "passport" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "number" BIGINT NOT NULL UNIQUE,
    "division_code" VARCHAR(7),
    "registration" VARCHAR(255),
    "date_of_birth" DATE,
    "place_of_birth" VARCHAR(255),
    "place_of_issue" VARCHAR(255),
    "gender" VARCHAR(8),
    "photo_id" INT  UNIQUE REFERENCES "visitorphoto" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_passport_number_f209d3" ON "passport" ("number");
CREATE INDEX IF NOT EXISTS "idx_passport_photo_i_accf33" ON "passport" ("photo_id");
COMMENT ON COLUMN "passport"."number" IS 'Номер паспорта';
COMMENT ON COLUMN "passport"."division_code" IS 'Код подразделения';
COMMENT ON COLUMN "passport"."registration" IS 'Прописка';
COMMENT ON COLUMN "passport"."date_of_birth" IS 'Дата рождения';
COMMENT ON COLUMN "passport"."place_of_birth" IS 'Место рождения';
COMMENT ON COLUMN "passport"."place_of_issue" IS 'Орган выдавший паспорт';
COMMENT ON COLUMN "passport"."gender" IS 'Пол';
COMMENT ON TABLE "passport" IS 'Данные паспорта';
CREATE TABLE IF NOT EXISTS "visitor" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "deleted" BOOL NOT NULL  DEFAULT False,
    "first_name" VARCHAR(24) NOT NULL,
    "last_name" VARCHAR(24) NOT NULL,
    "middle_name" VARCHAR(24),
    "who_invited" VARCHAR(255),
    "destination" VARCHAR(128),
    "company_name" VARCHAR(255),
    "date_of_birth" DATE,
    "attribute" VARCHAR(64),
    "phone" VARCHAR(24),
    "email" VARCHAR(36),
    "visit_purpose" VARCHAR(255),
    "visit_start_date" TIMESTAMPTZ,
    "visit_end_date" TIMESTAMPTZ,
    "claim_id" INT REFERENCES "claim" ("id") ON DELETE CASCADE,
    "pass_id_id" INT REFERENCES "pass" ("id") ON DELETE CASCADE,
    "transport_id" INT REFERENCES "transport" ("id") ON DELETE CASCADE,
    "visitor_photo_id" INT REFERENCES "visitorphoto" ("id") ON DELETE CASCADE,
    "military_id_id" INT  UNIQUE REFERENCES "militaryid" ("id") ON DELETE CASCADE,
    "international_passport_id" INT  UNIQUE REFERENCES "internationalpassport" ("id") ON DELETE CASCADE,
    "passport_id" INT  UNIQUE REFERENCES "passport" ("id") ON DELETE CASCADE,
    "drive_license_id" INT  UNIQUE REFERENCES "drivelicense" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_visitor_phone_86a24d" ON "visitor" ("phone");
CREATE INDEX IF NOT EXISTS "idx_visitor_email_2fcbe1" ON "visitor" ("email");
CREATE INDEX IF NOT EXISTS "idx_visitor_militar_1177ae" ON "visitor" ("military_id_id");
CREATE INDEX IF NOT EXISTS "idx_visitor_interna_4551f1" ON "visitor" ("international_passport_id");
CREATE INDEX IF NOT EXISTS "idx_visitor_passpor_c75999" ON "visitor" ("passport_id");
CREATE INDEX IF NOT EXISTS "idx_visitor_drive_l_ece27a" ON "visitor" ("drive_license_id");
COMMENT ON COLUMN "visitor"."first_name" IS 'Имя';
COMMENT ON COLUMN "visitor"."last_name" IS 'Фамилия';
COMMENT ON COLUMN "visitor"."middle_name" IS 'Отчество';
COMMENT ON COLUMN "visitor"."who_invited" IS 'Кто пригласил?';
COMMENT ON COLUMN "visitor"."destination" IS 'Куда идет?';
COMMENT ON COLUMN "visitor"."company_name" IS 'организация посетителя';
COMMENT ON COLUMN "visitor"."date_of_birth" IS 'Дата рождения';
COMMENT ON COLUMN "visitor"."attribute" IS 'признак (иностранец)';
COMMENT ON COLUMN "visitor"."visit_purpose" IS 'цель посещения';
COMMENT ON COLUMN "visitor"."visit_start_date" IS 'дата или период посещения';
COMMENT ON COLUMN "visitor"."visit_end_date" IS 'дата или период посещения';
COMMENT ON TABLE "visitor" IS 'Посетитель';
CREATE TABLE IF NOT EXISTS "blacklist" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "level" VARCHAR(24),
    "visitor_id" INT NOT NULL REFERENCES "visitor" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_blacklist_visitor_8b0392" ON "blacklist" ("visitor_id");
COMMENT ON COLUMN "blacklist"."level" IS 'Уровни нарушений';
COMMENT ON TABLE "blacklist" IS 'Черный список';
CREATE TABLE IF NOT EXISTS "visitsession" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "enter" TIMESTAMPTZ,
    "exit" TIMESTAMPTZ,
    "visitor_id" INT NOT NULL REFERENCES "visitor" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_visitsessio_visitor_8d0719" ON "visitsession" ("visitor_id");
COMMENT ON COLUMN "visitsession"."enter" IS 'Зашел на территорию';
COMMENT ON COLUMN "visitsession"."exit" IS 'Вышел с территории';
COMMENT ON TABLE "visitsession" IS 'Время посещения';
CREATE TABLE IF NOT EXISTS "watermark" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "text" VARCHAR(255),
    "image" BYTEA
);
COMMENT ON COLUMN "watermark"."text" IS 'Текстовый водяной знак';
COMMENT ON COLUMN "watermark"."image" IS 'Водяной знак картинка';
COMMENT ON TABLE "watermark" IS 'Водяной знак для изображений';
CREATE TABLE IF NOT EXISTS "zone" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "modified_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(128) NOT NULL
);
COMMENT ON COLUMN "zone"."name" IS 'Название территории';
COMMENT ON TABLE "zone" IS 'Зоны доступа, разрешенные для посещения';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "claimway_system_user" (
    "claimway_id" INT NOT NULL REFERENCES "claimway" ("id") ON DELETE CASCADE,
    "systemuser_id" INT NOT NULL REFERENCES "systemuser" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "claimway_role" (
    "claimway_id" INT NOT NULL REFERENCES "claimway" ("id") ON DELETE CASCADE,
    "role_id" INT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "enablescope_role" (
    "enablescope_id" INT NOT NULL REFERENCES "enablescope" ("id") ON DELETE CASCADE,
    "role_id" INT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "claimtozone_zone" (
    "claimtozone_id" INT NOT NULL REFERENCES "claimtozone" ("id") ON DELETE CASCADE,
    "zone_id" INT NOT NULL REFERENCES "zone" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "systemuser_scopes" (
    "systemuser_id" INT NOT NULL REFERENCES "systemuser" ("id") ON DELETE CASCADE,
    "role_id" INT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "transport_claim" (
    "transport_id" INT NOT NULL REFERENCES "transport" ("id") ON DELETE CASCADE,
    "claim_id" INT NOT NULL REFERENCES "claim" ("id") ON DELETE CASCADE
);
