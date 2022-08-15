-- upgrade --
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
-- downgrade --
DROP TABLE IF EXISTS "pushsubscription";
