import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

import '../../../../core/error/exceptions.dart';
import '../../domain/entities/conversation.dart';
import '../models/chat_models.dart';

/// Talks to the backend AI Chat endpoints, including the Server-Sent Events
/// stream used for assistant replies.
class ChatRemoteDataSource {
  const ChatRemoteDataSource(this._dio);
  final Dio _dio;

  Future<List<ConversationModel>> listConversations() async {
    final resp = await _dio.get<List<dynamic>>('/chat/conversations');
    _ensure(resp);
    return (resp.data ?? [])
        .map((e) => ConversationModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<ConversationModel> createConversation({String? title}) async {
    final resp = await _dio.post<Map<String, dynamic>>(
      '/chat/conversations',
      data: {if (title != null && title.isNotEmpty) 'title': title},
    );
    _ensure(resp);
    return ConversationModel.fromJson(resp.data!);
  }

  Future<ConversationDetailModel> getConversation(String id) async {
    final resp =
        await _dio.get<Map<String, dynamic>>('/chat/conversations/$id');
    _ensure(resp);
    return ConversationDetailModel.fromJson(resp.data!);
  }

  Future<ConversationModel> renameConversation(String id, String title) async {
    final resp = await _dio.patch<Map<String, dynamic>>(
      '/chat/conversations/$id',
      data: {'title': title},
    );
    _ensure(resp);
    return ConversationModel.fromJson(resp.data!);
  }

  Future<void> deleteConversation(String id) async {
    final resp = await _dio.delete<Map<String, dynamic>>(
      '/chat/conversations/$id',
    );
    _ensure(resp);
  }

  /// POSTs a message and yields parsed SSE events as they stream back.
  Stream<ChatStreamEvent> sendMessage({
    required String conversationId,
    required String content,
  }) async* {
    final resp = await _dio.post<ResponseBody>(
      '/chat/conversations/$conversationId/messages',
      data: {'content': content},
      options: Options(
        responseType: ResponseType.stream,
        headers: {'Accept': 'text/event-stream'},
      ),
    );

    if ((resp.statusCode ?? 500) >= 400) {
      throw ServerException('Failed to send message.',
          statusCode: resp.statusCode);
    }

    final body = resp.data!;
    var buffer = '';
    await for (final chunk in body.stream) {
      buffer += utf8.decode(chunk, allowMalformed: true);
      // SSE frames are separated by a blank line.
      int sep;
      while ((sep = buffer.indexOf('\n\n')) != -1) {
        final frame = buffer.substring(0, sep);
        buffer = buffer.substring(sep + 2);
        final event = _parseFrame(frame);
        if (event != null) yield event;
      }
    }
  }

  ChatStreamEvent? _parseFrame(String frame) {
    for (final line in frame.split('\n')) {
      final trimmed = line.trimLeft();
      if (!trimmed.startsWith('data:')) continue;
      final payload = trimmed.substring(5).trim();
      if (payload.isEmpty) continue;
      final json = jsonDecode(payload) as Map<String, dynamic>;
      switch (json['type']) {
        case 'delta':
          return ChatDelta(json['text'] as String? ?? '');
        case 'done':
          return ChatDone(
            messageId: json['message_id'] as String? ?? '',
            content: json['content'] as String? ?? '',
          );
        case 'error':
          return ChatStreamError(json['detail'] as String? ?? 'Stream error.');
      }
    }
    return null;
  }

  void _ensure(Response<dynamic> resp) {
    final code = resp.statusCode ?? 0;
    if (code >= 200 && code < 300) return;
    final data = resp.data;
    final detail = data is Map<String, dynamic> ? data['detail'] as String? : null;
    throw ServerException(detail ?? 'Request failed.', statusCode: code);
  }
}
