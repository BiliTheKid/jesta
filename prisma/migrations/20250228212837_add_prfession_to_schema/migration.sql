/*
  Warnings:

  - You are about to drop the column `profession` on the `Professional` table. All the data in the column will be lost.
  - Added the required column `professionId` to the `Professional` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "Professional" DROP COLUMN "profession",
ADD COLUMN     "professionId" INTEGER NOT NULL;

-- CreateTable
CREATE TABLE "Profession" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,

    CONSTRAINT "Profession_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Profession_name_key" ON "Profession"("name");

-- AddForeignKey
ALTER TABLE "Professional" ADD CONSTRAINT "Professional_professionId_fkey" FOREIGN KEY ("professionId") REFERENCES "Profession"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
