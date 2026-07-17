import 'package:dartz/dartz.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:krishna_ai/core/error/failures.dart';
import 'package:krishna_ai/features/chat/domain/entities/chat_message.dart';
import 'package:krishna_ai/features/chat/domain/entities/conversation.dart';
import 'package:krishna_ai/features/chat/domain/repositories/chat_repository.dart';
import 'package:krishna_ai/features/chat/presentation/providers/chat_controller.dart';
import 'package:krishna_ai/features/chat/presentation/providers/chat_providers.dart';

/// A hand-written fake so the controller can be tested without a backend.
class _FakeChatRepository implements ChatRepository {
  _FakeChatRepository({this.streamError = false});
  final bool streamError;

  @override
  Future<Either<Failure, ConversationDetail>> getConversation(String id) async {
    return Right(
      ConversationDetail(
        id: id,
        title: 'Test',
        createdAt: DateTime(2026),
        messages: const [],
      ),
    );
  }

  @override
  Stream<ChatStreamEvent> sendMessage({
    required String conversationId,
    required String content,
  }) async* {
    yield const ChatDelta('Hi');
    yield const ChatDelta(' there');
    if (streamError) {
      yield const ChatStreamError('boom');
    } else {
      yield const ChatDone(messageId: 'm1', content: 'Hi there');
    }
  }

  @override
  Future<Either<Failure, Conversation>> createConversation({String? title}) =>
      throw UnimplementedError();
  @override
  Future<Either<Failure, Unit>> deleteConversation(String id) =>
      throw UnimplementedError();
  @override
  Future<Either<Failure, List<Conversation>>> listConversations() =>
      throw UnimplementedError();
  @override
  Future<Either<Failure, Conversation>> renameConversation(
          String id, String title) =>
      throw UnimplementedError();
}

Future<void> _settle() => Future<void>.delayed(const Duration(milliseconds: 10));

void main() {
  test('accumulates streamed deltas into a completed assistant message',
      () async {
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(_FakeChatRepository()),
      ],
    );
    addTearDown(container.dispose);

    // Keep the autoDispose provider alive across async gaps.
    container.listen(chatControllerProvider('c1'), (_, __) {});
    final controller = container.read(chatControllerProvider('c1').notifier);
    await _settle(); // initial load

    await controller.send('hello');

    final state = container.read(chatControllerProvider('c1'));
    expect(state.isSending, isFalse);
    expect(state.messages.length, 2);
    expect(state.messages[0].role, MessageRole.user);
    expect(state.messages[0].content, 'hello');
    expect(state.messages[1].role, MessageRole.assistant);
    expect(state.messages[1].content, 'Hi there');
    expect(state.messages[1].isStreaming, isFalse);
  });

  test('surfaces a stream error while keeping partial text', () async {
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider
            .overrideWithValue(_FakeChatRepository(streamError: true)),
      ],
    );
    addTearDown(container.dispose);

    container.listen(chatControllerProvider('c2'), (_, __) {});
    final controller = container.read(chatControllerProvider('c2').notifier);
    await _settle();

    await controller.send('hello');

    final state = container.read(chatControllerProvider('c2'));
    expect(state.error, 'boom');
    expect(state.messages.last.content, 'Hi there');
    expect(state.messages.last.isStreaming, isFalse);
  });
}
