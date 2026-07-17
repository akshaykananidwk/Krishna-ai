/// Low-level exceptions thrown by data sources. These are caught in the
/// repository layer and converted into [Failure]s.
library;

class ServerException implements Exception {
  const ServerException(this.message, {this.statusCode, this.errorCode});

  final String message;
  final int? statusCode;
  final String? errorCode;

  @override
  String toString() => 'ServerException($statusCode, $errorCode): $message';
}

class NetworkException implements Exception {
  const NetworkException([this.message = 'No internet connection.']);
  final String message;
}

class CacheException implements Exception {
  const CacheException([this.message = 'Local storage error.']);
  final String message;
}

class UnauthorizedException implements Exception {
  const UnauthorizedException([this.message = 'Session expired.']);
  final String message;
}
