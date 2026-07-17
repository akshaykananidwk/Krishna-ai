import 'package:flutter_test/flutter_test.dart';
import 'package:krishna_ai/core/utils/validators.dart';

void main() {
  group('Validators.email', () {
    test('rejects empty and malformed', () {
      expect(Validators.email(''), isNotNull);
      expect(Validators.email('not-an-email'), isNotNull);
      expect(Validators.email('a@b'), isNotNull);
    });

    test('accepts a valid address', () {
      expect(Validators.email('arjuna@example.com'), isNull);
    });
  });

  group('Validators.password', () {
    test('enforces length and complexity', () {
      expect(Validators.password('short'), isNotNull);
      expect(Validators.password('alllowercase1'), isNotNull); // no uppercase
      expect(Validators.password('ALLUPPERCASE1'), isNotNull); // no lowercase
      expect(Validators.password('NoDigitsHere'), isNotNull); // no digit
      expect(Validators.password('Dharma123'), isNull);
    });
  });

  group('Validators.confirmPassword', () {
    test('matches against the source field', () {
      final validate = Validators.confirmPassword(() => 'Dharma123');
      expect(validate('Dharma123'), isNull);
      expect(validate('different'), isNotNull);
    });
  });
}
