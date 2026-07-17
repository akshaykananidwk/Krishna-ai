import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../network/dio_client.dart';
import '../storage/token_storage.dart';

/// Application-wide singletons wired with Riverpod (constructor injection under
/// the hood — no service locator, fully overridable in tests).

final tokenStorageProvider = Provider<TokenStorage>((ref) => TokenStorage());

final dioProvider = Provider<Dio>((ref) {
  final storage = ref.watch(tokenStorageProvider);
  return buildDioClient(tokenStorage: storage);
});
