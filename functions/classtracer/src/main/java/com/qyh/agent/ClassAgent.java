package com.qyh.agent;

import java.lang.instrument.Instrumentation;


public class ClassAgent {

    public static void premain(String argsString, Instrumentation inst) {
        String outputDir = null;
        String classesPath = null;
        String[] args = argsString.split(",");
        for (String arg : args) {
            String[] kv = arg.split("=");
            String key = kv[0];
            String value = kv[1];
            if (key.equals("outputDir")) {
                outputDir = value;
            } else if (key.equals("classesPath")) {
                classesPath = value;
            } else {
                System.out.println("unknown arg: " + key);
                return;
            }
        }
        if (outputDir == null || classesPath == null) {
            System.err.println("outputDir or classesPath is null");
            return;
        }

        ClassTransformer transformer = new ClassTransformer(outputDir, classesPath);
        inst.addTransformer(transformer);

    }
}