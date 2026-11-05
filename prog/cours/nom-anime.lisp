(defun generer-nom-anime (prenom age)
  (let* ((parties-nom '("Takahashi" "Fujimoto" "Yamamoto" "Kobayashi"
                        "Hoshino" "Abe" "Tanaka" "Matsumoto" "Sasaki" "Inoue"))
         ;; Un nombre calculé à partir du prénom : la somme des codes de ses lettres
         (nombre (reduce #'+ (map 'list #'char-code (string-downcase prenom))))
         (nom (nth (mod nombre (length parties-nom)) parties-nom))
         (honorifique
           (cond
             ((< age 13) "-chan")
             ((< age 18) (if (evenp nombre) "-kun" "-san"))
             ((< age 30) "-san")
             ((< age 50) "-sama")
             (t "-sensei"))))
    (format nil "~a~a ~a" nom honorifique prenom)))

(defun main ()
  (format t "Entrez votre vrai prénom : ")
  (finish-output)
  (let ((prenom (read-line)))
    (format t "Entrez votre âge : ")
    (finish-output)
    (let ((age (parse-integer (read-line))))
      (format t "Votre nom d'anime est : ~a~%" (generer-nom-anime prenom age)))))

;; Lancer le programme
(main)
