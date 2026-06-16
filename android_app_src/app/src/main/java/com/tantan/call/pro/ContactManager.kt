package com.tantan.call.pro

import android.content.Context
import android.provider.ContactsContract
import android.util.Log

data class BusinessContact(
    val id: String,
    val name: String,
    val phone: String,
    val tags: String = ""
)

object ContactManager {

    /**
     * 시스템 연락처 중 '동네비서' 그룹에 속한 연락처만 가져옵니다.
     */
    fun getBusinessContactsFromSystem(context: Context): List<BusinessContact> {
        val contacts = mutableListOf<BusinessContact>()
        
        try {
            // 1. '동네비서' 그룹 ID 찾기
            var groupId: String? = null
            val groupCursor = context.contentResolver.query(
                ContactsContract.Groups.CONTENT_URI,
                arrayOf(ContactsContract.Groups._ID, ContactsContract.Groups.TITLE),
                "${ContactsContract.Groups.TITLE} = ?",
                arrayOf("동네비서"),
                null
            )
            
            groupCursor?.use {
                if (it.moveToFirst()) {
                    groupId = it.getString(it.getColumnIndexOrThrow(ContactsContract.Groups._ID))
                }
            }
            
            if (groupId == null) {
                Log.d("DongneBiseo", "'동네비서' 그룹이 존재하지 않습니다.")
                return contacts
            }

            // 2. 해당 그룹에 속한 연락처 ID(CONTACT_ID)들 가져오기
            val contactIds = mutableSetOf<String>()
            val groupMemberUri = ContactsContract.Data.CONTENT_URI
            val groupMemberProjection = arrayOf(ContactsContract.Data.CONTACT_ID)
            val groupMemberSelection = "${ContactsContract.Data.MIMETYPE} = ? AND ${ContactsContract.CommonDataKinds.GroupMembership.GROUP_ROW_ID} = ?"
            val groupMemberSelectionArgs = arrayOf(
                ContactsContract.CommonDataKinds.GroupMembership.CONTENT_ITEM_TYPE,
                groupId!!
            )

            context.contentResolver.query(groupMemberUri, groupMemberProjection, groupMemberSelection, groupMemberSelectionArgs, null)?.use { cursor ->
                val idIndex = cursor.getColumnIndexOrThrow(ContactsContract.Data.CONTACT_ID)
                while (cursor.moveToNext()) {
                    contactIds.add(cursor.getString(idIndex))
                }
            }

            if (contactIds.isEmpty()) return contacts

            // 3. 찾은 CONTACT_ID들에 해당하는 이름과 전화번호 가져오기
            val phoneUri = ContactsContract.CommonDataKinds.Phone.CONTENT_URI
            val phoneProjection = arrayOf(
                ContactsContract.CommonDataKinds.Phone.CONTACT_ID,
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                ContactsContract.CommonDataKinds.Phone.NUMBER
            )
            
            // ID 리스트를 콤마로 연결하여 IN 절 생성 (개수가 많을 경우를 대비해 나눠서 처리하는 것이 좋으나 일단 단순 구현)
            val idListString = contactIds.joinToString(",") { "?" }
            val phoneSelection = "${ContactsContract.CommonDataKinds.Phone.CONTACT_ID} IN ($idListString)"
            val phoneSelectionArgs = contactIds.toTypedArray()

            context.contentResolver.query(phoneUri, phoneProjection, phoneSelection, phoneSelectionArgs, null)?.use { cursor ->
                val nameIndex = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
                val numberIndex = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.NUMBER)
                val contactIdIndex = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.CONTACT_ID)
                
                while (cursor.moveToNext()) {
                    val id = cursor.getString(contactIdIndex)
                    val name = cursor.getString(nameIndex)
                    val phone = cursor.getString(numberIndex)
                    
                    // 중복 방지 (한 연락처에 여러 번호가 있을 경우)
                    if (contacts.none { it.phone == phone }) {
                        contacts.add(BusinessContact(id, name, phone, "System"))
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("DongneBiseo", "연락처 가져오기 상세 실패: ${e.message}")
        }
        
        return contacts
    }
    
    /**
     * 특정 번호가 비즈니스 연락처인지 확인합니다.
     */
    fun isBusinessContact(context: Context, phoneNumber: String): Boolean {
        // 하이픈 제거 후 비교
        val normalized = phoneNumber.replace("-", "").replace(" ", "")
        val systemContacts = getBusinessContactsFromSystem(context)
        return systemContacts.any { it.phone.replace("-", "").replace(" ", "") == normalized }
    }
}
