type ImportRequestButtonProps = {
  isImporting: boolean;
  onImport: (file: File) => Promise<void>;
};

export function ImportRequestButton({ isImporting, onImport }: ImportRequestButtonProps) {
  return (
    <label className="button">
      Import Request
      <input
        type="file"
        accept=".zip,application/zip"
        disabled={isImporting}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            void onImport(file);
          }
          event.currentTarget.value = "";
        }}
      />
    </label>
  );
}
