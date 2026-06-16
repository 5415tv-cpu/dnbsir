package com.tantan.call.pro

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

class CallbackHistoryDBHelper(context: Context) : SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {

    companion object {
        private const val DATABASE_NAME = "CallbackHistory.db"
        private const val DATABASE_VERSION = 1
        const val TABLE_NAME = "history"
        const val COLUMN_ID = "id"
        const val COLUMN_PHONE = "phone_number"
        const val COLUMN_CALL_TYPE = "call_type"
        const val COLUMN_STATUS = "status"
        const val COLUMN_TIMESTAMP = "timestamp"
    }

    override fun onCreate(db: SQLiteDatabase) {
        val createTable = ("CREATE TABLE $TABLE_NAME ("
                + "$COLUMN_ID INTEGER PRIMARY KEY AUTOINCREMENT,"
                + "$COLUMN_PHONE TEXT,"
                + "$COLUMN_CALL_TYPE TEXT,"
                + "$COLUMN_STATUS TEXT,"
                + "$COLUMN_TIMESTAMP INTEGER"
                + ")")
        db.execSQL(createTable)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS $TABLE_NAME")
        onCreate(db)
    }

    fun insertHistory(phone: String, callType: String, status: String) {
        val db = this.writableDatabase
        val values = ContentValues()
        values.put(COLUMN_PHONE, phone)
        values.put(COLUMN_CALL_TYPE, callType)
        values.put(COLUMN_STATUS, status)
        values.put(COLUMN_TIMESTAMP, System.currentTimeMillis())

        db.insert(TABLE_NAME, null, values)
        db.close()
    }

    fun getRecentHistory(limit: Int = 50): List<CallbackHistory> {
        val historyList = mutableListOf<CallbackHistory>()
        val db = this.readableDatabase
        val cursor = db.rawQuery("SELECT * FROM $TABLE_NAME ORDER BY $COLUMN_TIMESTAMP DESC LIMIT $limit", null)

        if (cursor.moveToFirst()) {
            do {
                val phone = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_PHONE))
                val callType = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_CALL_TYPE))
                val status = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_STATUS))
                val timestamp = cursor.getLong(cursor.getColumnIndexOrThrow(COLUMN_TIMESTAMP))
                historyList.add(CallbackHistory(phone, callType, status, timestamp))
            } while (cursor.moveToNext())
        }
        cursor.close()
        db.close()
        return historyList
    }
}

data class CallbackHistory(
    val phoneNumber: String,
    val callType: String,
    val status: String,
    val timestamp: Long
)
