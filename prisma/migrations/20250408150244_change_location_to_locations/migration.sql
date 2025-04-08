/*
  Warnings:

  - You are about to drop the column `location` on the `ServiceCall` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "ServiceCall" DROP COLUMN "location",
ADD COLUMN     "locations" TEXT[];
